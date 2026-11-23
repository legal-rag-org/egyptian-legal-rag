from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Any


class AgentStepResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    agent_step_uuid: UUID
    iteration: int
    step_type: str
    tool_name: str | None
    tool_call_id: str | None
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    status: str
    duration_ms: int | None
    error: str | None
    created_at: datetime


class AgentExecutionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    agent_execution_uuid: UUID
    status: str
    total_iterations: int
    started_at: datetime
    completed_at: datetime | None
    error: str | None

    steps: list[AgentStepResponse]
