import logging

from .schemes import MemoryExtractionResponse

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode




class MemoryExtractor:

    def __init__(self, generation_model, template_parser):

        self.generation_model = generation_model
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")
        self.tracer = trace.get_tracer(__name__)

    async def extract_memories(
        self,
        conversation: str,
        previous_summary: str | None = None,
        language: str = "en",
    ) -> list[dict] | None:

        with self.tracer.start_as_current_span(
            "memory.extraction"
        ) as span:

            span.set_attribute(
                "memory.extraction.input_length",
                len(conversation) if isinstance(conversation, str) else 0
            )

            try:

                if not isinstance(conversation, str) or not conversation.strip():
                    self.logger.warning(
                        "Memory extraction received an empty conversation."
                    )

                    span.set_attribute("memory.extraction.failed", True)
                    span.set_status(Status(StatusCode.OK))

                    return None

                memory_extraction_prompt = self.template_parser.get(
                    group="rag",
                    key="memory_extraction_prompt",
                    vars={
                        "conversation": conversation,
                        "previous_summary": previous_summary or "",
                    },
                )

                response = await self.generation_model.generate_structured(
                    prompt=memory_extraction_prompt,
                    output_schema=MemoryExtractionResponse,
                )

                if response is None:

                    self.logger.warning(
                        "Memory extraction returned None."
                    )

                    span.set_attribute("memory.extraction.fallback", True)
                    span.set_status(Status(StatusCode.OK))

                    return None

                validated_memories = []
                seen_contents = set()

                for memory in response.memories:

                    normalized_content = memory.content.casefold()

                    if normalized_content in seen_contents:
                        continue

                    seen_contents.add(normalized_content)

                    validated_memories.append({
                        "content": memory.content,
                        "memory_type": memory.memory_type,
                        "importance": memory.importance,
                    })

                span.set_attribute(
                    "memory.extraction.memory_count",
                    len(validated_memories)
                )

                span.set_attribute(
                    "memory.extraction.fallback",
                    False
                )

                span.set_status(Status(StatusCode.OK))

                return validated_memories

            except Exception as exc:

                self.logger.exception(
                    "Error while extracting user memories."
                )

                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))

                return None
