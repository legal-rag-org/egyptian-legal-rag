import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any


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

    async def run(self, query: str, context: AgentContext, max_iterations: int = 5):
        messages = list(context.chat_history)
        messages.append({"role": "user", "content": query})

        tools = self.tool_registry.get_schemas()
        rag_result = None

        for iteration in range(1, max_iterations + 1):

            message = await self.llm.generate_with_tools(
                messages=messages,
                tools=tools,
            )

            if not message:
                self.logger.warning("LLM returned no message at iteration %d", iteration)
                return self._build_result(
                    answer="حصلت مشكلة في الاتصال بالموديل، حاول تاني.",
                    rag_result=rag_result,
                )

            tool_calls = getattr(message, "tool_calls", None)

            # FINAL ANSWER
            if not tool_calls:
                return self._build_result(answer=message.content, rag_result=rag_result)

            # ASSISTANT TOOL CALL
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

            # EXECUTE TOOLS
            results = await asyncio.gather(
                *(self._handle_tool_call(tc, context) for tc in tool_calls)
            )

            for tool_call, tool_result in results:
                if tool_call.function.name == "rag_search" and "error" not in tool_result:
                    rag_result = tool_result

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        self.logger.warning("Agent hit max_iterations=%d without a final answer", max_iterations)
        return self._build_result(
            answer="تعذر إكمال الطلب باستخدام الأدوات المتاحة.",
            rag_result=rag_result,
        )

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

    def _build_result(self, answer=None, rag_result=None):
        rag_result = rag_result or {}
        return {
            "answer": answer,
            "full_prompt": rag_result.get("full_prompt"),
            "retrieved_documents": rag_result.get("retrieved_documents", []),
            "filters": rag_result.get("filters", {}),
            "citations": rag_result.get("citations", []),
        }