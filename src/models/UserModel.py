from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import User
from sqlalchemy import select
import bcrypt

from uuid import UUID

class UserModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def get_user_by_email(self, email: str):
        async with self.db_client() as session:

            search_stmt = select(User).where(
                User.email == email
            )

            result = await session.execute(search_stmt)

            return result.scalar_one_or_none()

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
    ):
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
        )

        async with self.db_client() as session:
            async with session.begin():
                session.add(user)

            await session.refresh(user)

        return user

    async def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    async def get_user_by_uuid(self, user_uuid: UUID):
        async with self.db_client() as session:
            search_stmt = select(User).where(
                User.user_uuid == user_uuid
            )

            result = await session.execute(search_stmt)

            return result.scalar_one_or_none()