from enum import Enum
from pydantic import BaseModel, Field, model_validator


class MemoryConsolidationAction(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    REINFORCE = "reinforce"
    SKIP = "skip"
    CONFLICT = "conflict"


class MemoryConsolidationResponse(BaseModel):

    action: MemoryConsolidationAction

    target_memory_id: int | None = Field(
        default=None,
        gt=0,
        description="ID of the existing memory affected by the decision."
    )

    updated_content: str | None = Field(
        default=None,
        min_length=1,
        description="Updated memory content when the action is update."
    )

    reason: str = Field(
        min_length=1,
        description="Explanation for the selected action."
    )

    @model_validator(mode="after")
    def validate_action_data(self):

        if self.action == MemoryConsolidationAction.INSERT:

            if self.target_memory_id is not None:
                raise ValueError(
                    "Insert action must not have a target_memory_id."
                )

            if self.updated_content is not None:
                raise ValueError(
                    "Insert action must not have updated_content."
                )

        elif self.action == MemoryConsolidationAction.UPDATE:

            if self.target_memory_id is None:
                raise ValueError(
                    "Update action requires target_memory_id."
                )

            if not self.updated_content or not self.updated_content.strip():
                raise ValueError(
                    "Update action requires non-empty updated_content."
                )

        elif self.action in (
            MemoryConsolidationAction.REINFORCE,
            MemoryConsolidationAction.SKIP,
            MemoryConsolidationAction.CONFLICT,
        ):

            if self.target_memory_id is None:
                raise ValueError(
                    f"{self.action.value} action requires target_memory_id."
                )

            if self.updated_content is not None:
                raise ValueError(
                    f"{self.action.value} action must not have updated_content."
                )

        return self
