from ..ToolInterface import ToolInterface
from services.AgentService import AgentContext
from .RAGToolEnums import RAGToolEnums

class RAGTool(ToolInterface):

    def __init__(self):
        self._rag_handler = None

    def set_rag_handler(self, rag_handler):
        self._rag_handler = rag_handler

    @property
    def name(self) -> str:
        return RAGToolEnums.NAME.value

    @property
    def description(self) -> str:
        return RAGToolEnums.DESCRIPTION.value



    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "The question or search query "
                                "to search in the knowledge base."
                            ),
                        }
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(
        self,
        project,
        query: str,
        limit: int = 10,
        retrieval_limit: int = 20,
        chat_history: list | None = None,
        expanded_queries: list[str] = None,
    ):

        if self._rag_handler is None:
            return {
                "error": "RAG handler is not configured."
            }

        return await self._rag_handler(
            project=project,
            query=query,
            limit=limit,
            retrieval_limit=retrieval_limit,
            chat_history=chat_history,
            expanded_queries=expanded_queries,
        )

    async def execute_with_context(self, arguments: dict, context: AgentContext) -> dict:
        result = await self.execute(
            project=context.project,
            query=arguments.get("query"),
            limit=context.limit,
            retrieval_limit=context.retrieval_limit,
            chat_history=context.chat_history,
            expanded_queries=context.expanded_queries,
        )

        if not result:
            return {"error": "RAG returned no result."}

        answer, full_prompt, _, retrieved_documents, filters, citations = result

        return {
            "answer": answer,
            "full_prompt": full_prompt,
            "retrieved_documents": self._serialize_retrieved_documents(retrieved_documents),
            "filters": filters,
            "citations": citations,
        }

    def _serialize_retrieved_documents(self, documents):
        return [
            {"text": d.text, "score": d.score, "source": d.source, "page": d.page}
            for d in documents
        ]