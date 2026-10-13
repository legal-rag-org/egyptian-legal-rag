from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import Conversation
from sqlalchemy import func, select, delete

from uuid import UUID

class ConversationModel(BaseDataModel):

    def __init__(self, db_client : object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def insert_conversation(self, conversation: Conversation):
    
        async with self.db_client() as session:
            async with session.begin():
                session.add(conversation)
        
            await session.refresh(conversation)
        
        return conversation
    

    async def get_conversation_by_uuid_and_project_id(
                    self,
                    conversation_uuid : UUID,
                    project_id: int
        ):
        async with self.db_client() as session:

            search_stmt = select(Conversation).where(
                Conversation.conversation_uuid == conversation_uuid,
                Conversation.conversation_project_id == project_id
            )

            result = await session.execute(search_stmt)

            return result.scalar_one_or_none()

    
    async def get_or_create_conversation(
        self,
        project_id: int,
        user_id: int,
        conversation_uuid: UUID | None = None,
        title: str = "محادثة جديدة",
    ):
        if conversation_uuid is not None:
            conversation = (
                await self.get_conversation_by_uuid_project_and_user(
                    conversation_uuid=conversation_uuid,
                    project_id=project_id,
                    user_id=user_id,
                )
            )

            if conversation is None:
                return None

            return conversation

        conversation = Conversation(
            title=title,
            conversation_project_id=project_id,
            conversation_user_id=user_id,
        )

        return await self.insert_conversation(conversation=conversation)

        

    
    async def get_conversation(
        self,
        conversation_id: int,
    ):
        async with self.db_client() as session:
            stmt = select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    

    async def insert_many_conversations(self, conversations: list, batch_size: int = 100):

        if batch_size < 1:
             raise ValueError("batch_size must be >= 1")
    
        async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(conversations), batch_size):
                        batch = conversations[i : batch_size + i]
                        session.add_all(batch)
                

        return len(conversations)
    

    async def delete_conversations_by_project_id(self, project_id: int):
                
        async with self.db_client() as session:
            async with session.begin():

                delete_stmt = delete(Conversation).where(Conversation.conversation_project_id == project_id)
                result = await session.execute(delete_stmt)

        return result.rowcount
    

    async def get_conversations_by_project_id(self, project_id: int,
                                                 page_no: int=1,
                                                 page_size: int=50):
    
            if page_no < 1:
                raise ValueError("page_no must be >= 1")

            if not 1 <= page_size <= 100:
                raise ValueError("page_size must be between 1 and 100")
    
            async with self.db_client() as session:
                  
                  search_stmt = (
                        select(Conversation)
                        .where(
                            Conversation.conversation_project_id == project_id
                        )
                        .order_by(Conversation.created_at.desc())
                        .offset((page_no - 1) * page_size)
                        .limit(page_size)
                    )
                  result = await session.execute(search_stmt)
    
                  records = result.scalars().all()
    
            return records
    

    async def get_total_conversation_count(self, project_id: int):
             async with self.db_client() as session:
                  
                  count_sql = select(
                        func.count(Conversation.conversation_id)
                        ).where(
                        Conversation.conversation_project_id == project_id
                   )
    
                  records_count = await session.execute(count_sql)
    
                  return records_count.scalar_one()

    async def update_summary(
        self,
        conversation_id: int,
        summary: str,
    ):
        async with self.db_client() as session:
            async with session.begin():

                search_stmt = select(Conversation).where(
                    Conversation.conversation_id == conversation_id
                )

                result = await session.execute(search_stmt)
                conversation = result.scalar_one_or_none()

                if conversation is None:
                    raise ValueError(
                        f"Conversation {conversation_id} not found."
                    )

                conversation.summary = summary

            await session.refresh(conversation)

        return conversation


    
    async def get_conversations_by_user_and_project(
        self,
        user_id: int,
        project_id: int,
        page_no: int = 1,
        page_size: int = 50,
    ):
        if page_no < 1:
            raise ValueError("page_no must be >= 1")

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")

        async with self.db_client() as session:
            stmt = (
                select(Conversation)
                .where(
                    Conversation.conversation_user_id == user_id,
                    Conversation.conversation_project_id == project_id,
                )
                .order_by(
                    Conversation.updated_at.desc().nullslast(),
                    Conversation.created_at.desc(),
                )
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )

            result = await session.execute(stmt)
            return result.scalars().all()


    async def get_conversation_by_uuid_project_and_user(
        self,
        conversation_uuid: UUID,
        project_id: int,
        user_id: int,
    ):
        async with self.db_client() as session:
            stmt = select(Conversation).where(
                Conversation.conversation_uuid == conversation_uuid,
                Conversation.conversation_project_id == project_id,
                Conversation.conversation_user_id == user_id,
            )

            result = await session.execute(stmt)
            return result.scalar_one_or_none()

