import logging
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

class QueryRewriting:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")

        self.tracer = trace.get_tracer(__name__)


    
    async def rewrite(
        self,
        rewrite_query: str,
        rewrite_history: str | None = "",
        previous_summary: str | None = ""
    ) -> str:

        with self.tracer.start_as_current_span(
            "rag.query_rewriting"
        ) as span:

            try:
                query_rewriter_prompt = self.template_parser.get(
                    group="rag",
                    key="query_rewriter_prompt",
                    vars={
                        "chat_history": rewrite_history,
                        "previous_summary": previous_summary,
                        "query": rewrite_query
                    }
                )

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

                    span.set_attribute(
                        "rag.query_rewriting.fallback",
                        True
                    )

                    span.set_status(Status(StatusCode.OK))

                    return rewrite_query

                span.set_attribute(
                    "rag.query_rewriting.fallback",
                    False
                )

                span.set_status(Status(StatusCode.OK))

                return rewritten_query

            except Exception as exc:

                self.logger.exception(
                    "Error while generating rewritten query "
                    "falling back to original query"
                )

                span.record_exception(exc)

                span.set_attribute(
                    "rag.query_rewriting.fallback",
                    True
                )

                span.set_status(
                    Status(
                        StatusCode.OK,
                        "Query rewriting failed; using original query"
                    )
                )

                return rewrite_query


