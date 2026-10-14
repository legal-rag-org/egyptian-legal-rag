import json
import logging

from models.db_schemes.insurance_rag.schemes.data_chunk import RetrievedDocument

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
    expanded_queries: list[str] = field(default_factory=list)

class AgentService:

    def __init__(
        self,
        llm,
        tool_registry,
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.logger = logging.getLogger("uvicorn")

    async def run(
            self,
            query: str,
            context: AgentContext,
            max_iterations: int = 5
    ):

        messages = list(context.chat_history)

        messages.append({
            "role": "user",
            "content": query,
        })

        tools = self.tool_registry.get_schemas()
        rag_result = None

        for _ in range(max_iterations):

            message = self.llm.generate_with_tools(
                messages=messages,
                tools=tools,
            )

            if not message:
                return self._build_result()

            tool_calls = getattr(
                message,
                "tool_calls",
                None,
            )

            # FINAL ANSWER
            if not tool_calls:
                return self._build_result(answer=message.content, rag_result=rag_result)

            # ASSISTANT TOOL CALL
            assistant_message = {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [],
            }

            for tool_call in tool_calls:

                assistant_message["tool_calls"].append({
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                })

            messages.append(assistant_message)

            # EXECUTE TOOLS
            for tool_call in tool_calls:

                tool_name = tool_call.function.name

                tool = self.tool_registry.get(
                    tool_name
                )

                if tool is None:

                    tool_result = {
                        "error": (
                            f"Tool '{tool_name}' "
                            "was not found."
                        )
                    }

                else:

                    try:

                        arguments = json.loads(
                            tool_call.function.arguments
                        )

                    except json.JSONDecodeError:

                        self.logger.error(
                            "Invalid arguments for tool %s: %s",
                            tool_name,
                            tool_call.function.arguments,
                        )

                        tool_result = {
                            "error": "Invalid tool arguments."
                        }

                    else:

                        tool_result = await self._execute_tool(
                            tool=tool,
                            tool_name=tool_name,
                            arguments=arguments,
                            context=context,
                        )

                        if tool_name == "rag_search" and "error" not in tool_result:
                            rag_result = tool_result

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
                })

        return self._build_result(answer="تعذر إكمال الطلب باستخدام الأدوات المتاحة.")

    async def _execute_tool(self, tool, tool_name: str, arguments: dict, context: AgentContext):
        try:
            return await tool.execute_with_context(arguments, context)
        except Exception as e:
            self.logger.error("Tool %s failed: %s", tool_name, e)
            return {"error": f"Tool '{tool_name}' failed to execute."}



    def _build_result(self, answer=None, rag_result=None):
        rag_result = rag_result or {}
        return {
            "answer": answer,
            "full_prompt": rag_result.get("full_prompt"),
            "retrieved_documents": rag_result.get("retrieved_documents", []),
            "filters": rag_result.get("filters", {}),
            "citations": rag_result.get("citations", []),
        }