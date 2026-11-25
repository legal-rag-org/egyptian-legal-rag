import logging

from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


Domain = Literal[
    "insurance",
    "labour",
    "tax",
    "civil_service",
    "companies",
    "customs",
    "reconciliation"
]

LawNumber = Literal[
    "148", "14", "91", "67",
    "81", "159", "207", "187"
]

LawYear = Literal[
    "2019", "2025", "2005", "2016",
    "1981", "2020", "2023"
]


class MetadataFilters(BaseModel):

    model_config = ConfigDict(extra="forbid")

    domain: Optional[list[Domain]] = None
    law_number: Optional[list[LawNumber]] = None
    law_year: Optional[list[LawYear]] = None


class MetadataExtraction(BaseModel):

    model_config = ConfigDict(extra="forbid")

    filters: MetadataFilters


class MetadataFilterExtractor:

    def __init__(self, generation_client, template_parser):
        self.generation_client = generation_client
        self.template_parser = template_parser
        self.logger = logging.getLogger("uvicorn.error")
        self.tracer = trace.get_tracer(__name__)

    async def extract(
        self,
        query: str,
        available_fields: list[str]
    ) -> dict:

        with self.tracer.start_as_current_span(
            "rag.metadata_filtering"
        ) as span:

            span.set_attribute(
                "rag.metadata.available_fields_count",
                len(available_fields)
            )

            try:
                metadata_filter_extractor_prompt = self.template_parser.get(
                    group="rag",
                    key="metadata_filter_extractor_prompt",
                    vars={
                        "available_fields": available_fields,
                        "query": query
                    }
                )

                response = await self.generation_client.generate_structured(
                    prompt=metadata_filter_extractor_prompt,
                    output_schema=MetadataExtraction
                )

                if response is None:
                    self.logger.warning(
                        "Metadata extraction returned None."
                    )

                    span.set_attribute("rag.metadata.fallback", True)
                    span.set_attribute("rag.metadata.filter_count", 0)
                    span.set_status(Status(StatusCode.OK))

                    return {}

                filters = response.filters.model_dump(exclude_none=True)

                filters = {
                    key: value
                    for key, value in filters.items()
                    if key in available_fields
                }

                span.set_attribute("rag.metadata.fallback", False)
                span.set_attribute(
                    "rag.metadata.filter_count",
                    len(filters)
                )
                span.set_attribute(
                    "rag.metadata.extracted_fields",
                    list(filters.keys())
                )
                span.set_status(Status(StatusCode.OK))

                return filters

            except Exception as exc:
                self.logger.exception(
                    "Metadata extraction error"
                )

                span.record_exception(exc)
                span.set_attribute("rag.metadata.fallback", True)
                span.set_attribute("rag.metadata.filter_count", 0)
                span.set_status(
                    Status(StatusCode.OK)
                )

                return {}
