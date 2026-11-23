import math

from .BaseController import BaseController

class AgentExecutionController(BaseController):

    def __init__(
        self,
        agent_execution_model: object,
        agent_step_model: object,
    ):
        self.agent_execution_model = agent_execution_model
        self.agent_step_model = agent_step_model

    async def get_executions_by_user(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        status: str | None = None,
        conversation_uuid=None,
    ):

        # Get executions
        executions = await self.agent_execution_model.get_executions_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            conversation_uuid=conversation_uuid,
        )

        # Get total count
        total = await self.agent_execution_model.count_executions_by_user(
            user_id=user_id,
            status=status,
            conversation_uuid=conversation_uuid,
        )

        # Calculate pagination metadata
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return {
            "items": executions,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        }

    
    async def get_execution_by_uuid(
        self,
        execution_uuid,
        user_id: int,
    ):

        execution = await self.agent_execution_model.get_execution_by_uuid_and_user(
            execution_uuid=execution_uuid,
            user_id=user_id,
        )

        if execution is None:
            return None

        return execution



    async def get_execution_steps(
        self,
        execution_uuid,
        user_id: int,
    ):

        execution = await self.agent_execution_model.get_execution_by_uuid_and_user(
            execution_uuid=execution_uuid,
            user_id=user_id,
        )

        if execution is None:
            return None

        steps = await self.agent_step_model.get_steps_by_execution_id(
            execution_id=execution.agent_execution_id
        )

        return steps

