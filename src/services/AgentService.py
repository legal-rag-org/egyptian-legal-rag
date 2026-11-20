import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import time


from utils.agent_metrics import (
    AGENT_LLM_CALLS,
    AGENT_LLM_DURATION,
    AGENT_LLM_TOKENS,
    AGENT_TOOL_CALLS,
    AGENT_TOOL_DURATION
    
)


DUPLICATE_CALL_ERROR = (
    "You already made this exact tool call in this conversation. "
    "Use the earlier result, or change the arguments / approach."
)

@dataclass
class AgentContext:
    project: Any

    chat_history: list = field(default_factory=list)

    limit: int = 10
    retrieval_limit: int = 20

    latitude: float | None = None
    longitude: float | None = None

    # Adaptive RAG
    routing_plan: dict = field(default_factory=dict)
    search_queries: list[str] = field(default_factory=list)
    metadata_filters: dict = field(default_factory=dict)
    hyde_passages: list[str] = field(default_factory=list)


class AgentService:

    def __init__(self, llm, tool_registry):
        self.llm = llm
        self.tool_registry = tool_registry
        self.logger = logging.getLogger("uvicorn")

        
    
    async def run(
        self,
        query: str,
        context: AgentContext,
        execution_id: int,
        step_model,
        max_iterations: int = 5,
    ):
        messages = list(context.chat_history)
        messages.append({"role": "user", "content": query})

        tools = self.tool_registry.get_schemas()

        rag_result = None
        seen_calls: set[str] = set()
        trace: list[dict] = []

        for iteration in range(1, max_iterations + 1):

            # 1. Ask LLM
            start_time = time.perf_counter()

            try:
                llm_response = await self.llm.generate_with_tools_detailed(
                    messages=messages,
                    tools=tools,
                )

                llm_duration_ms = (
                    time.perf_counter() - start_time
                ) * 1000

                message = llm_response.message

                if not message:
                    raise RuntimeError("LLM returned an empty message")

                provider = llm_response.provider or "unknown"

                # LLM Metrics

                AGENT_LLM_CALLS.labels(
                    provider=provider,
                    status="success",
                ).inc()

                AGENT_LLM_DURATION.labels(
                    provider=provider,
                ).observe(llm_duration_ms / 1000)

                usage = llm_response.usage or {}

                AGENT_LLM_TOKENS.labels(
                    provider=provider,
                    token_type="prompt",
                ).inc(usage.get("prompt_tokens", 0))

                AGENT_LLM_TOKENS.labels(
                    provider=provider,
                    token_type="completion",
                ).inc(usage.get("completion_tokens", 0))

                # Save LLM Step in Database
                llm_output = {
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        }
                        for call in (message.tool_calls or [])
                    ],
                    "model": llm_response.model,
                    "provider": llm_response.provider,
                    "usage": llm_response.usage,
                    "finish_reason": llm_response.finish_reason,
                }

                await step_model.create_step(
                    execution_id=execution_id,
                    iteration=iteration,
                    step_type="llm_call",
                    status="success",
                    input_data={
                        "messages": messages,
                        "tools": tools,
                    },
                    output_data=llm_output,
                    duration_ms=llm_duration_ms,
                )

                # Save LLM Trace
                trace.append({
                    "iteration": iteration,
                    "step_type": "llm_call",
                    "input_data": {
                        "messages": messages,
                        "tools": tools,
                    },
                    "output_data": llm_output,
                    "status": "success",
                    "duration_ms": llm_duration_ms,
                    "error": None,
                })

            except Exception as exc:

                llm_duration_ms = (
                    time.perf_counter() - start_time
                ) * 1000

                # Failed LLM Metrics
                AGENT_LLM_CALLS.labels(
                    provider="unknown",
                    status="error",
                ).inc()

                AGENT_LLM_DURATION.labels(
                    provider="unknown",
                ).observe(llm_duration_ms / 1000)

                error_data = {
                    "iteration": iteration,
                    "step_type": "llm_call",
                    "input_data": {
                        "messages": messages,
                        "tools": tools,
                    },
                    "output_data": None,
                    "status": "failed",
                    "duration_ms": llm_duration_ms,
                    "error": str(exc),
                }

                trace.append(error_data)

                await step_model.create_step(
                    execution_id=execution_id,
                    iteration=iteration,
                    step_type="llm_call",
                    status="failed",
                    input_data=error_data["input_data"],
                    duration_ms=llm_duration_ms,
                    error=str(exc),
                )

                raise

            # 2. Check for final answer
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                return self._build_result(
                    answer=message.content,
                    rag_result=rag_result,
                    status="done",
                    iterations=iteration,
                    trace=trace,
                )

            # 3. Append assistant tool calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # 4. Prepare tool execution
            outcomes = [None] * len(tool_calls)
            durations = [0] * len(tool_calls)

            pending = []

            for i, tc in enumerate(tool_calls):

                key = self._call_key(tc)

                if key in seen_calls:

                    result = {
                        "error": DUPLICATE_CALL_ERROR
                    }

                    try:
                        input_data = json.loads(
                            tc.function.arguments or "{}"
                        )

                        if not isinstance(input_data, dict):
                            input_data = {
                                "raw_arguments": tc.function.arguments
                            }

                    except (json.JSONDecodeError, TypeError):
                        input_data = {
                            "raw_arguments": tc.function.arguments
                        }


                    AGENT_TOOL_CALLS.labels(
                        tool_name=tc.function.name,
                        status="failed",
                    ).inc()

                    # Save duplicate tool step
                    await step_model.create_step(
                        execution_id=execution_id,
                        iteration=iteration,
                        step_type="tool_call",
                        status="failed",
                        tool_name=tc.function.name,
                        tool_call_id=tc.id,
                        input_data=input_data,
                        output_data=result,
                        duration_ms=0,
                        error=DUPLICATE_CALL_ERROR,
                    )

                    outcomes[i] = result

                else:
                    seen_calls.add(key)
                    pending.append(i)

            # 5. Execute tools in parallel
            async def execute_with_timing(index: int):

                tool_call = tool_calls[index]

                start_time = time.perf_counter()

                _, result = await self._handle_tool_call(
                    tool_call,
                    context,
                )

                tool_duration_ms = int(
                    (time.perf_counter() - start_time) * 1000
                )

                # Parse tool arguments
                try:
                    input_data = json.loads(
                        tool_call.function.arguments or "{}"
                    )

                    if not isinstance(input_data, dict):
                        input_data = {
                            "raw_arguments": tool_call.function.arguments
                        }

                except (json.JSONDecodeError, TypeError):
                    input_data = {
                        "raw_arguments": tool_call.function.arguments
                    }

                is_success = "error" not in result

                # Tool Metrics
                tool_name = tool_call.function.name

                AGENT_TOOL_CALLS.labels(
                    tool_name=tool_name,
                    status="success" if is_success else "failed",
                ).inc()

                AGENT_TOOL_DURATION.labels(
                    tool_name=tool_name,
                ).observe(tool_duration_ms / 1000)

                # Persist tool step immediately
                await step_model.create_step(
                    execution_id=execution_id,
                    iteration=iteration,
                    step_type="tool_call",
                    status="success" if is_success else "failed",
                    tool_name=tool_call.function.name,
                    tool_call_id=tool_call.id,
                    input_data=input_data,
                    output_data=result,
                    duration_ms=tool_duration_ms,
                    error=str(result["error"]) if not is_success else None,
                )

                return index, result, tool_duration_ms

            executed = await asyncio.gather(
                *(execute_with_timing(i) for i in pending)
            )

            for i, result, tool_duration_ms in executed:

                outcomes[i] = result
                durations[i] = tool_duration_ms

            # 6. Save tool traces and append results
            for i, (tool_call, tool_result) in enumerate(
                zip(tool_calls, outcomes)
            ):

                if (
                    tool_call.function.name == "rag_search"
                    and "error" not in tool_result
                ):
                    rag_result = tool_result

                # Parse arguments
                try:
                    input_data = json.loads(
                        tool_call.function.arguments or "{}"
                    )

                    if not isinstance(input_data, dict):
                        input_data = {
                            "raw_arguments": tool_call.function.arguments
                        }

                except (json.JSONDecodeError, TypeError):
                    input_data = {
                        "raw_arguments": tool_call.function.arguments
                    }

                is_success = "error" not in tool_result

                # Save tool trace
                trace.append({
                    "iteration": iteration,
                    "step_type": "tool_call",
                    "tool_name": tool_call.function.name,
                    "tool_call_id": tool_call.id,
                    "input_data": input_data,
                    "output_data": tool_result,
                    "status": "success" if is_success else "failed",
                    "duration_ms": durations[i],
                    "error": (
                        str(tool_result["error"])
                        if not is_success
                        else None
                    ),
                })

                # Append tool result to messages
                content = json.dumps(
                    tool_result,
                    ensure_ascii=False,
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": content,
                })

        # 7. Max iterations reached
        return self._build_result(
            answer="تعذر إكمال الطلب باستخدام الأدوات المتاحة.",
            rag_result=rag_result,
            status="max_iterations",
            iterations=max_iterations,
            trace=trace,
        )


    def _call_key(self, tool_call) -> str:
        raw = tool_call.function.arguments or "{}"

        try:
            # sort for {"a" : 1, "b" : 2} to be the same as {"b" : 2, "a" : 1}
            raw = json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

        return f"{tool_call.function.name}: {raw}"

    async def _handle_tool_call(self, tool_call, context: AgentContext):
        name = tool_call.function.name
        raw_args = tool_call.function.arguments

        tool = self.tool_registry.get(name)
        if tool is None:
            return tool_call, {"error": f"Tool '{name}' was not found."}

        try:
            arguments = json.loads(raw_args or "{}")
        except json.JSONDecodeError as e:
            self.logger.error("Invalid arguments for tool %s: %s", name, raw_args)
            return tool_call, {
                "error": f"Invalid JSON in tool arguments: {e.msg} (position {e.pos}). "
                         "Send a valid JSON object."
            }

        if not isinstance(arguments, dict):
            return tool_call, {"error": "Tool arguments must be a JSON object."}

        result = await self._execute_tool(tool, name, arguments, context)
        return tool_call, result

    async def _execute_tool(self, tool, tool_name: str, arguments: dict, context: AgentContext):
        try:
            return await tool.execute_with_context(arguments, context)
        except Exception as e:
            self.logger.exception("Tool %s failed", tool_name)
            return {"error": f"Tool '{tool_name}' failed ({type(e).__name__})."}

    def _build_result(self, answer=None, rag_result=None,
                  status="done", iterations=0, trace=None):
        rag_result = rag_result or {}
        return {
            "answer": answer,
            "status": status,
            "iterations": iterations,
            "trace": trace or [],
            "full_prompt": rag_result.get("full_prompt"),
            "retrieved_documents": rag_result.get("retrieved_documents", []),
            "filters": rag_result.get("filters", {}),
            "citations": rag_result.get("citations", []),
        }