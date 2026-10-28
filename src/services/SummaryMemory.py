import logging


class SummaryMemory:

    def __init__(self, generation_client, template_parser):
        self.generation_client = generation_client
        self.template_parser = template_parser

        self.logger = logging.getLogger("uvicorn.error")


    async def summarize(self, conversation, previous_summary: str | None = None):

        summary_memory_prompt = self.template_parser.get(
            group="rag",
            key="summary_memory_prompt",
            vars={
                "conversation": conversation,
                "previous_summary":previous_summary or "",
            },
        )

        try:
            response = await self.generation_client.generate_text(
                prompt=summary_memory_prompt
            )

            summary = response.strip()

            if not summary:
                self.logger.warning(
                    "Summary memory generation returned an empty response."
                )

                return previous_summary or ""

            return summary

        except Exception:
            self.logger.exception(
                "Error while generating conversation summary."
            )

            return previous_summary or ""