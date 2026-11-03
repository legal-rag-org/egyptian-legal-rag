import logging

class QueryRewriting:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")


    async def rewrite(self, rewrite_query: str, rewrite_history: str | None = "", previous_summary: str | None = "") -> str:

        query_rewriter_prompt = self.template_parser.get(
            group="rag",
            key="query_rewriter_prompt",
            vars={
                "chat_history": rewrite_history,
                "previous_summary": previous_summary,
                "query": rewrite_query
            }
        )

        try:


            response = await self.generation_model.generate_text(
                prompt=query_rewriter_prompt,
            )

            rewritten_query = None
            

            if isinstance(response, str) and response.strip():
                rewritten_query = response.strip()

            if not rewritten_query:
                self.logger.warning(
                    "Rewritten query generation returned an empty response"
                )

                return rewrite_query

            return rewritten_query

        except Exception:
            self.logger.exception(
                "Error while generating rewritten query falling back to original query"
            )

            return rewrite_query
            

