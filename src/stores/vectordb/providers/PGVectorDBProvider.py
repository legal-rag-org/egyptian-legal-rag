from ..VectorDBInterface import VectorDBInterface
from stores.vectordb.VectorDBEnums import (PgVectorDistanceMetodEnums, PgVectorIndexTypeEnums,
                                            PgVectorTableSchemeEnums, DistanceMethodEnums)
from models.db_schemes import RetrievedDocument
from helpers.metadata import FILTERABLE_METADATA
import logging
from typing import List
from sqlalchemy.sql import text as sql_text
import json
import re

class PGVectorProvider(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int=786, 
                 distance_method : str = None, index_threshold: int=100):


        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold= index_threshold

        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value

        if distance_method == DistanceMethodEnums.COSINE.value:
            distance_method = PgVectorDistanceMetodEnums.COSINE.value

        if distance_method == DistanceMethodEnums.DOT.value:
            distance_method = PgVectorDistanceMetodEnums.DOT.value

        self.distance_method = distance_method
        self.default_index_name = lambda collection_name : f"{collection_name}_vector_idx"
        self.logger = logging.getLogger("uvicorn")


    async def connect(self):

        async with self.db_client() as session:
            async with session.begin():

                await session.execute(
                    sql_text("CREATE EXTENSION IF NOT EXISTS vector")  
                )


    async def disconnect(self):
        pass


    async def is_collection_existed(self, collection_name: str) -> bool:
            
            async with self.db_client() as session:

                list_tbl = sql_text(
                    "SELECT * FROM pg_tables WHERE tablename = :collection_name"
                )

                results = await session.execute(
                    list_tbl,
                    {"collection_name" : collection_name}
                )

                record = results.scalar_one_or_none()

            return bool(record)

    

    async def list_all_collections(self) -> List:

        async with self.db_client() as session:
            
                list_tbl = sql_text(
                    "SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix"
                )

                results = await session.execute(
                    list_tbl, 
                    {"prefix": f"{self.pgvector_table_prefix}%"}
                )

                records = results.scalars().all()

        return records

    async def get_collection_info(self, collection_name: str) -> dict:
            
            async with self.db_client() as session:
                async with session.begin():

                    table_info_stmt = sql_text(
                        """
                        SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                        FROM pg_tables
                        WHERE tablename = :collection_name
                        """
                    )

                    count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')

                    table_info = await session.execute(
                        table_info_stmt,
                        {"collection_name" : collection_name}
                    )

                    result = await session.execute(count_sql)
                    
                    record_count = result.scalar()

                    table_data = table_info.mappings().one_or_none()
                    if not table_data:
                        return None

                    return {
                        "table_info" : dict(table_data),
                        "record_count" : record_count
                    }


    async def delete_collection(self, collection_name: str):

        if not collection_name.startswith(self.pgvector_table_prefix):
            raise ValueError("Invalid collection name")

        async with self.db_client() as session:
            async with session.begin():

                self.logger.info(
                    "Deleting collection: %s",
                    collection_name
                )

                delete_sql = sql_text(
                    f'DROP TABLE IF EXISTS "{collection_name}"'
                )

                await session.execute(delete_sql)

        return True


    async def create_collection(self, collection_name: str,
                                    embedding_size: int,
                                    do_reset: bool=False):
    
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)


        if not collection_name.startswith(self.pgvector_table_prefix):
                    raise ValueError("Invalid collection name")

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

        if not is_collection_existed:
                self.logger.info(f"Creating collection {collection_name}")

                async with self.db_client() as session:
                    async with session.begin():

                        create_sql = sql_text(
                        f'CREATE TABLE {collection_name} ('
                            f'{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY,'
                            f'{PgVectorTableSchemeEnums.TEXT.value} text, '
                            f'{PgVectorTableSchemeEnums.VECTOR.value} vector({embedding_size}), '
                            f'{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                            f'{PgVectorTableSchemeEnums.CHUNK_ID.value} integer, '
                            f'FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'
                            ')'
                        )

                        await session.execute(create_sql)

                return True

        
        return False

    async def is_index_existed(self, collection_name: str) -> bool:

        index_name = self.default_index_name(collection_name=collection_name)

        async with self.db_client() as session:

            check_sql = sql_text(f""" 
                                SELECT 1 
                                FROM pg_indexes 
                                WHERE tablename = :collection_name
                                AND indexname = :index_name
                                """
            )
            
            results = await session.execute(
                 check_sql, 
                 {"index_name": index_name,
                  "collection_name": collection_name}
            )
            
            return bool(results.scalar_one_or_none())



    async def create_vector_index(self, collection_name: str,
                                  index_type: str = PgVectorIndexTypeEnums.HNSW.value):

            is_index_existed = await self.is_index_existed(collection_name=collection_name)
            
            if is_index_existed:
                 self.logger.error(f"index is already created in {collection_name}")
                 return False

            async with self.db_client() as session:
                 async with session.begin():
                      
                      count_sql = sql_text(
                           f"SELECT COUNT(*) FROM {collection_name}"
                        )
                      
                      result = await session.execute(count_sql)
                      records_count = result.scalar_one()

                      if records_count < self.index_threshold:
                           return False

                      self.logger.info(f"Start creating vector index for collection : {collection_name}")

                      index_name = self.default_index_name(collection_name)
                      create_idx_sql = sql_text(
                            f'CREATE INDEX {index_name} ON {collection_name} '
                            f'USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method})'
                            )

                      await session.execute(create_idx_sql)
                      self.logger.info(f"End creating vector index for collection : {collection_name}")

            return True


    async def reset_vector_index(self, collection_name: str,
                                  index_type: str = PgVectorIndexTypeEnums.HNSW.value) -> bool:

            index_name = self.default_index_name(collection_name=collection_name)
            
            async with self.db_client() as session:
                async with session.begin():
                     
                     drop_sql = sql_text(
                          f"DROP INDEX IF EXISTS {index_name}"
                     )

                     result = await session.execute(drop_sql)


            return await self.create_vector_index(collection_name=collection_name, 
                                                  index_type=index_type)


    async def insert_one(self, collection_name: str,
                              text: str,
                              vector: list,
                              metadata: dict=None,
                              record_id: str=None):

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

        if not is_collection_existed:
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        if not record_id:
            self.logger.error(f"Can not insert new record without chunk_id: {collection_name}")
            return False
        
        async with self.db_client() as session:
            async with session.begin():

                insert_sql = sql_text(
                                    f"""
                                    INSERT INTO {collection_name}
                                    (
                                        {PgVectorTableSchemeEnums.TEXT.value},
                                        {PgVectorTableSchemeEnums.VECTOR.value},
                                        {PgVectorTableSchemeEnums.METADATA.value},
                                        {PgVectorTableSchemeEnums.CHUNK_ID.value}
                                    )
                                    VALUES (
                                        :text,
                                        :vector,
                                        :metadata,
                                        :chunk_id
                                    )
                                    """
                        )
                
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"

                await session.execute(insert_sql, {
                    'text': text,
                    'vector': "[" + ",".join([str(v) for v in vector]) + "]",
                    'metadata': metadata_json,
                    'chunk_id': record_id
                })


                await self.create_vector_index(
                     collection_name=collection_name
                )

        
        return True



    async def insert_many(self, collection_name: str,
                              texts: list,
                              vectors: list,
                              metadata: list=None,
                              record_ids: list=None,
                              batch_size: int=50):
    
            is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

            if not is_collection_existed:
                self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
                return False


            if len(vectors) != len(record_ids):
                self.logger.error(f'Invaild data items for collection: {collection_name}')
                return False

            if not metadata or len(metadata) == 0:
                metadata = [None] * len(texts)
                


            async with self.db_client() as session:
                async with session.begin():

                    for i in range(0, len(texts), batch_size):
                            batch_text = texts[i : i + batch_size]
                            batch_vector = vectors[i : i + batch_size]
                            batch_metdata = metadata[i : i + batch_size]
                            batch_record_ids = record_ids[i : i + batch_size]

                            values = []

                            for _text, _vector, _metadata, _record_id in zip(batch_text, batch_vector, batch_metdata, batch_record_ids):

                                meta_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"

                                values.append({
                                    'text': _text,
                                    'vector': "[" + ",".join([str(v) for v in _vector]) + "]",
                                    'metadata': meta_json,
                                    'chunk_id': _record_id
                                    })
                                
                                batch_insert_sql = sql_text(
                                    f"""
                                    INSERT INTO {collection_name}
                                    (
                                        {PgVectorTableSchemeEnums.TEXT.value},
                                        {PgVectorTableSchemeEnums.VECTOR.value},
                                        {PgVectorTableSchemeEnums.METADATA.value},
                                        {PgVectorTableSchemeEnums.CHUNK_ID.value}
                                    )
                                    VALUES (
                                        :text,
                                        :vector,
                                        :metadata,
                                        :chunk_id
                                    )
                                    """
                                )

                            await session.execute(batch_insert_sql, values)

            await self.create_vector_index(
                     collection_name=collection_name
                )


            return True


    def _build_metadata_filters(
        self,
        filters: dict | None,
        params: dict,
        param_prefix: str = "filter",
    ) -> list[str]:

        if not filters:
            return []

        conditions = []

        for index, (key, value) in enumerate(filters.items()):

            if key not in FILTERABLE_METADATA:
                continue

            # domain can contain multiple values
            if key == "domain":
                domains = value if isinstance(value, list) else [value]

                placeholders = []

                for domain_index, domain in enumerate(domains):
                    param_name = f"{param_prefix}_{index}_{domain_index}"

                    placeholders.append(f":{param_name}")
                    params[param_name] = str(domain)

                if placeholders:
                    conditions.append(
                        f"metadata->>'{key}' IN ({', '.join(placeholders)})"
                    )

            else:
                param_name = f"{param_prefix}_{index}"

                conditions.append(
                    f"metadata->>'{key}' = :{param_name}"
                )

                params[param_name] = str(value)

        return conditions

    
    async def search_by_vector(self, collection_name: str,
                                   vector: list,
                                   limit: int,
                                   filters: dict | None = None,) -> List[RetrievedDocument]:
            

            is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

            if not is_collection_existed:
                self.logger.error(f"Can not search into a non-existed collection: {collection_name}")
                return []
            
            vector = "[" + ",".join([str(v) for v in vector]) + "]"

            async with self.db_client() as session:
                    async with session.begin():
                        conditions = []

                        params = {
                            "vector": vector,
                            "limit": limit,
                        }

                        conditions.extend(
                            self._build_metadata_filters(
                                filters=filters,
                                params=params,
                                param_prefix="vector_filter",
                            )
                        )

                        where_clause = ""

                        if conditions:
                            where_clause = "WHERE " + " AND ".join(conditions)

                        search_sql = sql_text(
                            f"""
                            SELECT
                                {PgVectorTableSchemeEnums.TEXT.value} AS text,
                                {PgVectorTableSchemeEnums.METADATA.value} AS metadata,
                                1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) AS score
                            FROM {collection_name}
                            {where_clause}
                            ORDER BY score DESC
                            LIMIT :limit
                            """
                        )

                        result = await session.execute(
                            search_sql,
                            params
                        )

                        records = result.fetchall()

            return [
                RetrievedDocument(
                    text=record.text,
                    score=record.score,
                    source=record.metadata.get("source"),
                    page=record.metadata.get("page"),
                    file_url=record.metadata.get("file_url")
                )
                for record in records
            ]
                

    

    async def search_by_keyword(
    self,
    collection_name: str,
    query: str,
    limit: int,
    filters: dict | None = None,
) -> List[RetrievedDocument]:

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)

        if not is_collection_existed:
            self.logger.error(
                f"Can not search into a non-existed collection: {collection_name}"
            )
            return []

        async with self.db_client() as session:
            async with session.begin():

                conditions = [
                    f"""
                    to_tsvector(
                        'simple',
                        {PgVectorTableSchemeEnums.TEXT.value}
                    )
                    @@ plainto_tsquery('simple', :query)
                    """
                ]

                params = {
                    "query": query,
                    "limit": limit,
                }

                conditions.extend(
                    self._build_metadata_filters(
                        filters=filters,
                        params=params,
                        param_prefix="keyword_filter",
                    )
                )

                where_clause = " AND ".join(conditions)

                search_sql = sql_text(
                    f"""
                    SELECT
                        {PgVectorTableSchemeEnums.TEXT.value} AS text,
                        {PgVectorTableSchemeEnums.METADATA.value} AS metadata,
                        ts_rank(
                            to_tsvector(
                                'simple',
                                {PgVectorTableSchemeEnums.TEXT.value}
                            ),
                            plainto_tsquery('simple', :query)
                        ) AS score
                    FROM {collection_name}
                    WHERE {where_clause}
                    ORDER BY score DESC
                    LIMIT :limit
                    """
                )

                result = await session.execute(
                    search_sql,
                    params
                )

                records = result.fetchall()

        return [
            RetrievedDocument(
                text=record.text,
                score=record.score,
                source=record.metadata.get("source"),
                page=record.metadata.get("page"),
                file_url=record.metadata.get("file_url")
            )
            for record in records
        ]



    def arabic_to_english_digits(self, text: str) -> str:
        translation_table = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789"
        )

        return text.translate(translation_table)

    def english_to_arabic_digits(self, text: str) -> str:
        translation_table = str.maketrans(
            "0123456789",
            "٠١٢٣٤٥٦٧٨٩"
        )

        return text.translate(translation_table)

    async def search_by_numeric(
            self,
            collection_name: str,
            query: str,
            limit: int,
            filters: dict | None = None,
        ) -> List[RetrievedDocument]:

        is_collection_existed = await self.is_collection_existed(
            collection_name=collection_name
        )

        if not is_collection_existed:
            self.logger.error(
                f"Can not search into a non-existed collection: {collection_name}"
            )
            return []

        # Extract numeric tokens from query
        normalized_query = self.arabic_to_english_digits(query)

        numbers = re.findall(
            r"(?<!\d)\d+(?!\d)",
            normalized_query
        )

        if not numbers:
            return []

        async with self.db_client() as session:
            async with session.begin():

                conditions = []
                params = {
                    "limit": limit,
                }

                # Build numeric matching conditions
                numeric_conditions = []

                for index, number in enumerate(numbers):

                    param_name_en = f"number_en_{index}"
                    param_name_ar = f"number_ar_{index}"

                    arabic_number = self.english_to_arabic_digits(number)

                    numeric_conditions.append(
                        f"""
                        (
                            {PgVectorTableSchemeEnums.TEXT.value}
                            ~ ('(^|[^0-9])' || :{param_name_en} || '([^0-9]|$)')
                        )
                        OR
                        (
                            {PgVectorTableSchemeEnums.TEXT.value}
                            ~ ('(^|[^٠-٩])' || :{param_name_ar} || '([^٠-٩]|$)')
                        )
                        """
                    )

                    params[param_name_en] = number
                    params[param_name_ar] = arabic_number

                conditions.append(
                    "(" + " OR ".join(numeric_conditions) + ")"
                )

                # Metadata filters
                conditions.extend(
                    self._build_metadata_filters(
                        filters=filters,
                        params=params,
                        param_prefix="numeric_filter",
                    )
                )

                where_clause = " AND ".join(conditions)

                # Score = number of matched numeric tokens
                score_expressions = []

                for index, _ in enumerate(numbers):

                    param_name = f"number_{index}"

                    score_expressions.append(
                        f"""
                        CASE
                            WHEN
                                (
                                    {PgVectorTableSchemeEnums.TEXT.value}
                                    ~ ('(^|[^0-9])' || :number_en_{index} || '([^0-9]|$)')
                                )
                                OR
                                (
                                    {PgVectorTableSchemeEnums.TEXT.value}
                                    ~ ('(^|[^٠-٩])' || :number_ar_{index} || '([^٠-٩]|$)')
                                )
                            THEN 1
                            ELSE 0
                        END
                        """
                    )

                score_expression = " + ".join(score_expressions)

                search_sql = sql_text(
                    f"""
                    SELECT
                        {PgVectorTableSchemeEnums.TEXT.value} AS text,
                        {PgVectorTableSchemeEnums.METADATA.value} AS metadata,
                        ({score_expression})::float AS score

                    FROM {collection_name}

                    WHERE {where_clause}

                    ORDER BY score DESC

                    LIMIT :limit
                    """
                )

                result = await session.execute(
                    search_sql,
                    params
                )

                records = result.fetchall()

        return [
            RetrievedDocument(
                text=record.text,
                score=record.score,
                source=record.metadata.get("source"),
                page=record.metadata.get("page"),
                file_url=record.metadata.get("file_url")
            )
            for record in records
        ]
                    

            
                