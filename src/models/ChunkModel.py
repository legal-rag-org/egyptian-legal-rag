from .BaseDataModel import BaseDataModel
from models import Chunk
from sqlalchemy import func, select, delete

class ChunkModel(BaseDataModel):

    def __init__(self, db_client : object):
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance
    

    async def insert_chunk(self, chunk: Chunk):

        async with self.db_client() as session:
                    async with session.begin():
                        session.add(chunk)
        
        await session.refresh(chunk)
        
        return chunk

    async def get_chunk(self, chunk_id: int):
        async with self.db_client() as session:

               search_stmt = select(Chunk).where(
                    Chunk.chunk_id == chunk_id
               )
               result = await session.execute(search_stmt)

               chunk = result.scalar_one_or_none()

        return chunk

    async def insert_many_chunks(self, chunks: list, batch_size: int=100):

        async with self.db_client() as session:
             async with session.begin():
                  for i in range(0, len(chunks), batch_size):
                       batch = chunks[i : batch_size + i]
                       session.add_all(batch)
             

        return len(chunks)
    

    async def delete_chunks_by_project_id(self, project_id: int):
            
            async with self.db_client() as session:
              async with session.begin():

                dele_stmt = delete(Chunk).where(Chunk.chunk_project_id == project_id)
                result = await session.execute(dele_stmt)

            return result.rowcount
    

    async def get_chunks_by_project_id(self, project_id: int,
                                             page_no: int=1,
                                             page_size: int=50):

        if page_no < 1:
            raise ValueError("page must be >= 1")

        if page_size < 1:       
            raise ValueError("page_size must be >= 1")

        async with self.db_client() as session:
              
              search_stmt = select(Chunk).where(Chunk.chunk_project_id == project_id).offset((page_no - 1) * page_size).limit(page_size)
              result = await session.execute(search_stmt)

              records = result.scalars().all()

        return records

    async def get_chunks_by_asset_id(self, asset_id: int,
                                                 page_no: int=1,
                                                 page_size: int=50):
    
            if page_no < 1:
                raise ValueError("page must be >= 1")
    
            if page_size < 1:       
                raise ValueError("page_size must be >= 1")
    
            async with self.db_client() as session:
                  
                  search_stmt = select(Chunk).where(Chunk.chunk_asset_id == asset_id).offset((page_no - 1) * page_size).limit(page_size)
                  result = await session.execute(search_stmt)
    
                  records = result.scalars().all()
    
            return records

    async def get_total_chunk_count(self, project_id: int):
         async with self.db_client() as session:
              
              count_sql = select(
                    func.count(Chunk.chunk_id)
                    ).where(
                    Chunk.chunk_project_id == project_id
               )

              records_count = await session.execute(count_sql)

              return records_count.scalar_one()

    async def get_total_chunk_count_by_asset_id(
        self,
        asset_id: int
    ):
        async with self.db_client() as session:
            stmt = (
                select(func.count())
                .select_from(Chunk)
                .where(Chunk.chunk_asset_id == asset_id)
            )

            result = await session.execute(stmt)

        return result.scalar_one()


    

    

    

    

    