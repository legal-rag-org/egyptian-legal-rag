from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import UserMemory

from sqlalchemy import select, update, delete, func


class UserMemoryModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def insert_memory(self, memory: UserMemory):

        async with self.db_client() as session:
            async with session.begin():
                session.add(memory)

            await session.refresh(memory)

        return memory

    async def insert_many_memories(
        self,
        memories: list,
        batch_size: int = 100,
    ):

        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")

        async with self.db_client() as session:
            async with session.begin():

                for i in range(0, len(memories), batch_size):
                    batch = memories[i : i + batch_size]
                    session.add_all(batch)

        return len(memories)

    async def get_memory_by_id(
        self,
        memory_id: int,
        user_id: int,
    ):

        async with self.db_client() as session:

            stmt = select(UserMemory).where(
                UserMemory.memory_id == memory_id,
                UserMemory.memory_user_id == user_id,
            )

            result = await session.execute(stmt)

            return result.scalar_one_or_none()

    async def get_memories_by_user(
        self,
        user_id: int,
        page_no: int = 1,
        page_size: int = 50,
        active_only: bool = True,
    ):

        if page_no < 1:
            raise ValueError("page_no must be >= 1")

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        async with self.db_client() as session:

            stmt = select(UserMemory).where(
                UserMemory.memory_user_id == user_id,
            )

            if active_only:
                stmt = stmt.where(UserMemory.is_active.is_(True))

            stmt = (
                stmt
                .order_by(
                    UserMemory.importance.desc(),
                    UserMemory.created_at.desc(),
                )
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )

            result = await session.execute(stmt)

            return result.scalars().all()

    async def update_memory(
        self,
        memory_id: int,
        user_id: int,
        content: str | None = None,
        embedding: list[float] | None = None,
        memory_type: str | None = None,
        importance: int | None = None,
    ):

        values = {}

        if content is not None:
            values["content"] = content

        if embedding is not None:
            values["embedding"] = embedding

        if memory_type is not None:
            values["memory_type"] = memory_type

        if importance is not None:
            values["importance"] = importance

        if not values:
            return False

        async with self.db_client() as session:
            async with session.begin():

                stmt = (
                    update(UserMemory)
                    .where(
                        UserMemory.memory_id == memory_id,
                        UserMemory.memory_user_id == user_id,
                    )
                    .values(
                        **values,
                        updated_at=func.now(),
                    )
                    .returning(UserMemory.memory_id)
                )

                result = await session.execute(stmt)

                updated_id = result.scalar_one_or_none()

                if updated_id is None:
                    return False

            return True

    async def deactivate_memory(
        self,
        memory_id: int,
        user_id: int,
    ):

        async with self.db_client() as session:
            async with session.begin():

                stmt = (
                    update(UserMemory)
                    .where(
                        UserMemory.memory_id == memory_id,
                        UserMemory.memory_user_id == user_id,
                    )
                    .values(
                        is_active=False,
                        updated_at=func.now(),
                    )
                    .returning(UserMemory.memory_id)
                )

                result = await session.execute(stmt)

                updated_id = result.scalar_one_or_none()

                if updated_id is None:
                    return False

            return True

    async def delete_memory(
        self,
        memory_id: int,
        user_id: int,
    ):

        async with self.db_client() as session:
            async with session.begin():

                stmt = (
                    delete(UserMemory)
                    .where(
                        UserMemory.memory_id == memory_id,
                        UserMemory.memory_user_id == user_id,
                    )
                    .returning(UserMemory.memory_id)
                )

                result = await session.execute(stmt)

                deleted_id = result.scalar_one_or_none()

                if deleted_id is None:
                    return False

            return True


    async def get_total_memories_count(
        self,
        user_id: int,
        active_only: bool = True,
    ):
        async with self.db_client() as session:

            stmt = select(
                func.count(UserMemory.memory_id)
            ).where(
                UserMemory.memory_user_id == user_id
            )

            if active_only:
                stmt = stmt.where(UserMemory.is_active.is_(True))

            result = await session.execute(stmt)

            return result.scalar_one()


    async def search_similar_memories(
        self,
        user_id: int,
        query_embedding: list[float],
        top_k: int = 5,
        max_distance: float | None = None,
    ):
        if top_k < 1:
            raise ValueError("top_k must be greater than 0")

        distance = UserMemory.embedding.cosine_distance(
            query_embedding
        ).label("distance")

        query = (
            select(UserMemory, distance)
            .where(
                UserMemory.memory_user_id == user_id,
                UserMemory.is_active.is_(True),
            )
            .order_by(distance.asc())
            .limit(top_k)
        )

        if max_distance is not None:
            query = query.where(distance <= max_distance)

        async with self.db_client() as session:
            result = await session.execute(query)
            rows = result.all()

            return [
                {
                    "memory": row[0],
                    "distance": float(row[1]),
                }
                for row in rows
            ]
