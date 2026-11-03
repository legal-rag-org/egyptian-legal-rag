import logging

from pydantic import BaseModel, ConfigDict


class PromptInjectionResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    is_injection: bool
    reason: str



import logging


class PromptInjectionDetector:

    def __init__(self, generation_client, template_parser):

        self.generation_client = generation_client
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")

    async def detect(self, query: str) -> dict:

        if not query or not query.strip():
            return {
                "is_injection": False,
                "reason": None
            }

        prompt = self.template_parser.get(
            group="rag",
            key="prompt_injection_detector_prompt",
            vars={
                "query": query
            }
        )

        try:
            response = await self.generation_client.generate_structured(
                prompt=prompt,
                output_schema=PromptInjectionResult
            )

            if response is None:
                self.logger.error(
                    "Prompt injection detection returned None"
                )

                return {
                    "is_injection": True,
                    "reason": "Detection failed."
                }

            self.logger.info(
                "Prompt injection detection: %s",
                response.model_dump()
            )

            return response.model_dump()

        except Exception:
            self.logger.exception(
                "Prompt injection detection failed"
            )

            return {
                "is_injection": True,
                "reason": "Failed to validate the input."
            }
        