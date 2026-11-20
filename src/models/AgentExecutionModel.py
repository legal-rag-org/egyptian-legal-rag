from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import AgentExecution

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload



class AgentExecutionModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def insert_execution(self, execution: AgentExecution):

        async with self.db_client() as session:
            async with session.begin():
                session.add(execution)

            await session.refresh(execution)

        return execution

    async def create_execution(
        self,
        conversation_id: int,
        user_message_id: int | None = None,
    ):

        execution = AgentExecution(
            execution_conversation_id=conversation_id,
            user_message_id=user_message_id,
            status="running",
        )

        return await self.insert_execution(execution)

    
    async def complete_execution(
        self,
        execution_id: int,
        assistant_message_id: int | None,
        total_iterations: int,
    ):

        async with self.db_client() as session:
            async with session.begin():

                stmt = select(AgentExecution).where(
                    AgentExecution.agent_execution_id == execution_id
                )

                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution is None:
                    raise ValueError(
                        f"AgentExecution {execution_id} not found."
                    )

                execution.assistant_message_id = assistant_message_id
                execution.total_iterations = total_iterations
                execution.status = "completed"
                execution.completed_at = func.now()

            await session.refresh(execution)

        return execution


    async def fail_execution(
        self,
        execution_id: int,
        error: str,
        total_iterations: int,
        assistant_message_id: int | None = None,
    ):

        async with self.db_client() as session:
            async with session.begin():

                stmt = select(AgentExecution).where(
                    AgentExecution.agent_execution_id == execution_id
                )

                result = await session.execute(stmt)
                execution = result.scalar_one_or_none()

                if execution is None:
                    raise ValueError(
                        f"AgentExecution {execution_id} not found."
                    )

                execution.status = "failed"
                execution.error = error
                execution.total_iterations = total_iterations
                execution.assistant_message_id = assistant_message_id
                execution.completed_at = func.now()

            await session.refresh(execution)

        return execution


    async def get_execution_by_id(self, execution_id: int):

        async with self.db_client() as session:

            stmt = (
                select(AgentExecution)
                .options(selectinload(AgentExecution.steps))
                .where(
                    AgentExecution.agent_execution_id == execution_id
                )
            )

            result = await session.execute(stmt)

            return result.scalar_one_or_none()

    async def get_executions_by_conversation_id(
        self,
        conversation_id: int,
    ):

        async with self.db_client() as session:

            stmt = (
                select(AgentExecution)
                .where(
                    AgentExecution.execution_conversation_id
                    == conversation_id
                )
                .order_by(AgentExecution.started_at.desc())
            )

            result = await session.execute(stmt)

            return result.scalars().all()
