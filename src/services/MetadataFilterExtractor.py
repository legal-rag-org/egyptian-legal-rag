import json
import logging


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
            response =  await self.generation_client.generate_text(
                prompt=metadata_filter_extractor_prompt
            )

            self.logger.info(
                f"Metadata raw response: {repr(response)}"
            )

            response = response.strip() if response else ""

            if not response:
                self.logger.warning(
                    "Metadata generation returned an empty response"
                )
                return {}

            result = json.loads(response)

            filters = result.get("filters", {})

            if not isinstance(filters, dict):
                return {}

            filters = {
                key: value
                for key, value in filters.items()
                if key in available_fields
            }

            return filters

        except Exception as e:
            self.logger.error(
                f"Metadata extraction error: {e}"
            )
            return {}