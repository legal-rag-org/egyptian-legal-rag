
import json
import logging

from .schemes.MemoryConsolidation import (
    MemoryConsolidationResponse,
    MemoryConsolidationAction,
)


class MemoryConsolidation:

    ALLOWED_MEMORY_TYPES = {
        "preference",
        "goal",
        "project",
        "fact",
        "constraint",
    }

    def __init__(
        self,
        generation_model,
        template_parser,
        user_memory_service,
    ):

        self.generation_model = generation_model
        self.template_parser = template_parser
        self.user_memory_service = user_memory_service

        self.logger = logging.getLogger("uvicorn.error")

    async def consolidate_memory(
        self,
        user_id: int,
        new_memory: dict,
        top_k: int = 5,
        max_distance: float | None = None,
    ) -> MemoryConsolidationResponse:

        # Step 1: Validate the new memory

        if not isinstance(new_memory, dict):
            raise ValueError("New memory must be a dictionary")

        content = new_memory.get("content")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                "New memory content must be a non-empty string"
            )

        content = content.strip()

        memory_type = new_memory.get("memory_type")

        if memory_type not in self.ALLOWED_MEMORY_TYPES:
            raise ValueError("Invalid memory type")

        importance = new_memory.get("importance", 3)

        if (
            not isinstance(importance, int)
            or isinstance(importance, bool)
            or not 1 <= importance <= 5
        ):
            raise ValueError(
                "Importance must be an integer between 1 and 5"
            )

        normalized_memory = {
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
        }

        # Step 2: Retrieve similar existing memories

        existing_results = await self.user_memory_service.get_memories(
            user_id=user_id,
            query=content,
            top_k=top_k,
            max_distance=max_distance,
        )

        # Step 3: Prepare candidates for comparison

        existing_memories = []

        for result in existing_results or []:

            memory = result["memory"]
            distance = result["distance"]

            existing_memories.append({
                "memory_id": memory.memory_id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "importance": memory.importance,
                "distance": float(distance),
            })

        # Step 4: No candidates means a new memory

        if not existing_memories:

            return MemoryConsolidationResponse(
                action=MemoryConsolidationAction.INSERT,
                target_memory_id=None,
                updated_content=None,
                reason="No similar existing memories were found.",
            )

        # Step 5: Build the consolidation prompt

        prompt = self.template_parser.get(
            group="rag",
            key="memory_consolidation_prompt",
            vars={
                "new_memory": json.dumps(
                    normalized_memory,
                    ensure_ascii=False,
                ),
                "existing_memories": json.dumps(
                    existing_memories,
                    ensure_ascii=False,
                ),
            },
        )

        # Step 6: Ask the LLM to make a structured decision

        response = await self.generation_model.generate_structured(
            prompt=prompt,
            output_schema=MemoryConsolidationResponse,
        )

        if response is None:
            raise RuntimeError(
                "Memory consolidation returned an empty response"
            )

        if not isinstance(response, MemoryConsolidationResponse):
            raise TypeError(
                "Invalid memory consolidation response type"
            )

        # Step 7: Validate the target memory

        action = response.action

        if action == MemoryConsolidationAction.INSERT:

            if response.target_memory_id is not None:
                raise ValueError(
                    "Insert action must not have a target memory ID"
                )

        else:

            candidate_ids = {
                memory["memory_id"]
                for memory in existing_memories
            }

            if response.target_memory_id not in candidate_ids:
                raise ValueError(
                    "LLM returned an invalid target memory ID"
                )

        # Step 8: Log the consolidation decision

        self.logger.info(
            "Memory consolidation decision: action=%s, "
            "target_memory_id=%s",
            action.value,
            response.target_memory_id,
        )

        return response
