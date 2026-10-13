from .BaseDataModel import BaseDataModel
from .db_schemes.insurance_rag.schemes import Message
from sqlalchemy import func, select, delete

class MessageModel(BaseDataModel):

    def __init__(self, db_client : object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance
    

    async def insert_message(self, message: Message):
        
        async with self.db_client() as session:
            async with session.begin():
                session.add(message)
        
            await session.refresh(message)
        
        return message
    

    async def get_message(self, message_id: int):
        async with self.db_client() as session:

                search_stmt = select(Message).where(
                    Message.message_id == message_id
                )
                result = await session.execute(search_stmt)

                message = result.scalar_one_or_none()

        return message


    async def insert_many_messages(self, messages: list, batch_size: int=100):

        if batch_size < 1:
                     raise ValueError("batch_size must be >= 1")
        
        async with self.db_client() as session:
                async with session.begin():
                    for i in range(0, len(messages), batch_size):
                        batch = messages[i : batch_size + i]
                        session.add_all(batch)
                

        return len(messages)
    

    async def delete_messages_by_conversation_id(self, conversation_id: int):
                    
            async with self.db_client() as session:
                async with session.begin():
    
                    delete_stmt = delete(Message).where(Message.message_conversation_id == conversation_id)
                    result = await session.execute(delete_stmt)
    
            return result.rowcount
    

    async def get_messages_by_conversation_id(self, conversation_id: int,
                                                     page_no: int=1,
                                                     page_size: int=50):
        
                if page_no < 1:
                    raise ValueError("page_no must be >= 1")

                if not 1 <= page_size <= 100:
                    raise ValueError("page_size must be between 1 and 100")
        
                async with self.db_client() as session:
                      
                      search_stmt = (
                            select(Message)
                            .where(
                                Message.message_conversation_id == conversation_id
                            )
                            .order_by(Message.created_at.asc())
                            .offset((page_no - 1) * page_size)
                            .limit(page_size)
                        )
                      result = await session.execute(search_stmt)
        
                      records = result.scalars().all()
        
                return records
    

    async def get_total_messages_count(self, conversation_id: int):
        async with self.db_client() as session:
            
            count_sql = select(
                func.count(Message.message_id)
                ).where(
                Message.message_conversation_id == conversation_id
            )

            records_count = await session.execute(count_sql)

            return records_count.scalar_one()

    
