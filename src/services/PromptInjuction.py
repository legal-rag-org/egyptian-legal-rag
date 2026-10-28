import json
import logging



class PromptInjectionDetector:

    def __init__(self, generation_client, template_parser):

        self.generation_client = generation_client
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")


    async def detect(self, query: str) -> bool:

        if not query or not query.strip():
            return False

        prompt_injection_detector_prompt = self.template_parser.get(
            group="rag",
            key="prompt_injection_detector_prompt",
            vars={
                "query": query
            }
        )

        try:
            response = await self.generation_client.generate_text(
                prompt=prompt_injection_detector_prompt,
            )

            result = json.loads(response)

            return {
                "is_injection": bool(
                    result.get("is_injection", False)
                ),
                "reason": result.get("reason"),
            }

        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            self.logger.exception(
                "Prompt injection detection failed: %s",
                exc,
            )

            return {
                "is_injection": True,
                "reason": "Failed to validate the input.",
            }