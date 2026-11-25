import logging

from pydantic import BaseModel, ConfigDict

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class PromptInjectionResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    is_injection: bool
    reason: str


class PromptInjectionDetector:

    def __init__(self, generation_client, template_parser):

        self.generation_client = generation_client
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")
        self.tracer = trace.get_tracer(__name__)

    async def detect(self, query: str) -> dict:

        with self.tracer.start_as_current_span(
            "rag.prompt_injection_detection"
        ) as span:

            if not query or not query.strip():
                span.set_attribute("security.check_status", "skipped")
                span.set_attribute("security.injection_detected", False)
                span.set_status(Status(StatusCode.OK))

                return {
                    "is_injection": False,
                    "reason": None
                }

            try:
                prompt = self.template_parser.get(
                    group="rag",
                    key="prompt_injection_detector_prompt",
                    vars={
                        "query": query
                    }
                )

                response = await self.generation_client.generate_structured(
                    prompt=prompt,
                    output_schema=PromptInjectionResult
                )

                if response is None:
                    self.logger.error(
                        "Prompt injection detection returned None"
                    )

                    span.set_attribute("security.check_status", "failed")
                    span.set_attribute("security.injection_detected", True)
                    span.set_attribute("security.fail_closed", True)
                    span.set_status(
                        Status(StatusCode.ERROR, "Detection returned None")
                    )

                    return {
                        "is_injection": True,
                        "reason": "Detection failed."
                    }

                result = response.model_dump()

                span.set_attribute(
                    "security.injection_detected",
                    response.is_injection
                )
                span.set_attribute(
                    "security.check_status",
                    "blocked" if response.is_injection else "passed"
                )
                span.set_attribute("security.fail_closed", False)
                span.set_status(Status(StatusCode.OK))

                self.logger.info(
                    "Prompt injection detection: %s",
                    result
                )

                return result

            except Exception as exc:
                self.logger.exception(
                    "Prompt injection detection failed"
                )

                span.record_exception(exc)
                span.set_attribute("security.check_status", "failed")
                span.set_attribute("security.injection_detected", True)
                span.set_attribute("security.fail_closed", True)
                span.set_status(
                    Status(StatusCode.ERROR, "Prompt injection detection failed")
                )

                return {
                    "is_injection": True,
                    "reason": "Failed to validate the input."
                }
