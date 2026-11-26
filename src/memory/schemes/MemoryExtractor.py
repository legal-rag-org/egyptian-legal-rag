from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedMemory(BaseModel):

    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        min_length=1,
        description="A concise, self-contained memory explicitly supported by user messages."
    )

    memory_type: str = Field(
        description="One of: preference, goal, project, fact, constraint."
    )

    importance: int = Field(
        ge=1,
        le=5,
        description="Importance score between 1 and 5."
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Memory content cannot be empty.")

        return value

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, value: str) -> str:

        allowed_types = {
            "preference",
            "goal",
            "project",
            "fact",
            "constraint",
        }

        if value not in allowed_types:
            raise ValueError("Invalid memory type.")

        return value


class MemoryExtractionResponse(BaseModel):

    model_config = ConfigDict(extra="forbid")

    memories: list[ExtractedMemory] = Field(
        description="List of useful, stable memories extracted from the user conversation."
    )
