
from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import AgentStep

from sqlalchemy import select
from sqlalchemy import delete


class AgentStepModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def insert_step(self, step: AgentStep):

        async with self.db_client() as session:
            async with session.begin():
                session.add(step)

            await session.refresh(step)

        return step

    async def create_step(
        self,
        execution_id: int,
        iteration: int,
        step_type: str,
        status: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ):

        step = AgentStep(
            step_execution_id=execution_id,
            iteration=iteration,
            step_type=step_type,
            status=status,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            error=error,
        )

        return await self.insert_step(step)

    async def get_step_by_id(self, step_id: int):

        async with self.db_client() as session:

            stmt = select(AgentStep).where(
                AgentStep.agent_step_id == step_id
            )

            result = await session.execute(stmt)

            return result.scalar_one_or_none()

    async def get_steps_by_execution_id(
        self,
        execution_id: int,
    ):

        async with self.db_client() as session:

            stmt = (
                select(AgentStep)
                .where(
                    AgentStep.step_execution_id == execution_id
                )
                .order_by(AgentStep.agent_step_id.asc())
            )

            result = await session.execute(stmt)

            return result.scalars().all()

    async def delete_steps_by_execution_id(
        self,
        execution_id: int,
    ):

        async with self.db_client() as session:
            async with session.begin():

                stmt = delete(AgentStep).where(
                    AgentStep.step_execution_id == execution_id
                )

                result = await session.execute(stmt)

        return result.rowcount
