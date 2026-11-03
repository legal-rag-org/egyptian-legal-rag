import logging

from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal


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

    async def extract(
        self,
        query: str,
        available_fields: list[str]
    ) -> dict:

        metadata_filter_extractor_prompt = self.template_parser.get(
            group="rag",
            key="metadata_filter_extractor_prompt",
            vars={
                "available_fields": available_fields,
                "query": query
            }
        )

        try:
            response = await self.generation_client.generate_structured(
                prompt=metadata_filter_extractor_prompt,
                output_schema=MetadataExtraction
            )

            if response is None:
                return {}

            filters = response.filters.model_dump(exclude_none=True)

            filters = {
                key: value
                for key, value in filters.items()
                if key in available_fields
            }

            return filters

        except Exception:
            self.logger.exception(
                "Metadata extraction error"
            )
            return {}