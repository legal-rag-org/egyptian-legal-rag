import logging

from pydantic import BaseModel, ConfigDict, Field

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class QueryExpansionResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    expanded_queries: list[str] = Field(
        description="Alternative search queries preserving the original query's intent."
    )


class QueryExpansion:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")
        self.tracer = trace.get_tracer(__name__)

    async def expand(self, rewritten_query: str) -> list[str]:

        with self.tracer.start_as_current_span("rag.multi_query") as span:

            span.set_attribute("rag.query_expansion.input_length", len(rewritten_query))

            try:
                query_expansion_prompt = self.template_parser.get(
                    group="rag",
                    key="query_expansion_prompt",
                    vars={
                        "query": rewritten_query
                    }
                )

                response = await self.generation_model.generate_structured(
                    prompt=query_expansion_prompt,
                    output_schema=QueryExpansionResponse
                )

                if response is None:
                    self.logger.warning(
                        "Query expansion returned None. "
                        "Falling back to rewritten query."
                    )

                    span.set_attribute("rag.multi_query.fallback", True)
                    span.set_attribute("rag.multi_query.query_count", 1)
                    span.set_status(Status(StatusCode.OK))

                    return [rewritten_query]

                expanded_queries = [
                    query.strip()
                    for query in response.expanded_queries
                    if isinstance(query, str) and query.strip()
                ]

                expanded_queries = list(dict.fromkeys(expanded_queries))

                if not expanded_queries:
                    self.logger.warning(
                        "Query expansion returned empty queries. "
                        "Falling back to rewritten query."
                    )

                    span.set_attribute("rag.multi_query.fallback", True)
                    span.set_attribute("rag.multi_query.query_count", 1)
                    span.set_status(Status(StatusCode.OK))

                    return [rewritten_query]

                final_queries = list(dict.fromkeys([
                    rewritten_query,
                    *expanded_queries
                ]))

                span.set_attribute("rag.multi_query.fallback", False)
                span.set_attribute(
                    "rag.multi_query.generated_count",
                    len(expanded_queries)
                )
                span.set_attribute(
                    "rag.multi_query.query_count",
                    len(final_queries)
                )
                span.set_status(Status(StatusCode.OK))

                return final_queries

            except Exception as exc:
                self.logger.exception(
                    "Query expansion error. "
                    "Falling back to rewritten query."
                )

                span.record_exception(exc)
                span.set_attribute("rag.multi_query.fallback", True)
                span.set_attribute("rag.multi_query.query_count", 1)
                span.set_status(Status(StatusCode.OK))

                return [rewritten_query]
