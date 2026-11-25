
import logging

from pydantic import BaseModel, ConfigDict, Field

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class HyDEResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    hyde_passages: list[str] = Field(
        description="Hypothetical passages relevant to the search queries."
    )


class HyDE:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")
        self.tracer = trace.get_tracer(__name__)

    async def hyde_passages(
        self,
        search_queries: list[str]
    ) -> list[str]:

        with self.tracer.start_as_current_span("rag.hyde") as span:

            span.set_attribute(
                "hyde.input_query_count",
                len(search_queries)
            )

            try:
                hyde_prompt = self.template_parser.get(
                    group="rag",
                    key="hyde_prompt",
                    vars={
                        "queries": search_queries
                    },
                )

                response = await self.generation_model.generate_structured(
                    prompt=hyde_prompt,
                    output_schema=HyDEResponse
                )

                if response is None:
                    self.logger.warning(
                        "HyDE returned None. Falling back to search queries."
                    )

                    span.set_attribute("hyde.fallback", True)
                    span.set_attribute("hyde.passage_count", 0)
                    span.set_status(Status(StatusCode.OK))

                    return search_queries

                hyde_passages = [
                    passage.strip()
                    for passage in response.hyde_passages
                    if isinstance(passage, str) and passage.strip()
                ]

                hyde_passages = list(dict.fromkeys(hyde_passages))

                if not hyde_passages:
                    self.logger.warning(
                        "HyDE returned empty passages. "
                        "Falling back to search queries."
                    )

                    span.set_attribute("hyde.fallback", True)
                    span.set_attribute("hyde.passage_count", 0)
                    span.set_status(Status(StatusCode.OK))

                    return search_queries

                span.set_attribute("hyde.fallback", False)
                span.set_attribute(
                    "hyde.passage_count",
                    len(hyde_passages)
                )
                span.set_status(Status(StatusCode.OK))

                return hyde_passages

            except Exception as exc:
                self.logger.exception(
                    "HyDE generation error. "
                    "Falling back to search queries."
                )

                span.record_exception(exc)
                span.set_attribute("hyde.fallback", True)
                span.set_attribute("hyde.passage_count", 0)
                span.set_status(Status(StatusCode.OK))

                return search_queries
