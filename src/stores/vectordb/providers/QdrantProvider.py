from qdrant_client import models, QdrantClient
from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums
from models.db_schemes import RetrievedDocument
from qdrant_client.models import Filter, FieldCondition, MatchValue
from helpers.metadata import FILTERABLE_METADATA
import logging
from typing import List
import re

class QdrantProvider(VectorDBInterface):

    def __init__(self, db_client: str,
                   default_vector_size: int=786, 
                 distance_method : str = None, index_threshold: int=100):


        self.client = None

        self.db_client = db_client
        self.distance_method = None
        self.default_vector_size = default_vector_size

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = models.Distance.COSINE

        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT

        self.logger = logging.getLogger("uvicorn")


    async def connect(self):
        self.client = QdrantClient(path=self.db_client)

    async def disconnect(self):
        self.client = None

    async def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(
            collection_name=collection_name
        )

    async def list_all_collections(self) -> List:
        return self.client.get_collections()

    async def get_collection_info(self, collection_name: str) -> dict:
        info = self.client.get_collection(
            collection_name=collection_name
        )

        return {
            "status": info.status,
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }

    async def delete_collection(self, collection_name: str):

        if await self.is_collection_existed(collection_name=collection_name):
            self.logger.info(f"Deleting collection : {collection_name}")
            return self.client.delete_collection(collection_name=collection_name)

    async def create_collection(self, collection_name: str, 
                                embedding_size: int,
                                do_reset: bool = False):
        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)
        
        if not await self.is_collection_existed(collection_name):
            self.logger.info(f"createing new Qdrant collection: {collection_name}")
            _ =  self.client.create_collection(
                collection_name=collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=embedding_size,
                            distance=self.distance_method
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams(
                            modifier=models.Modifier.IDF
                        )
                    }
            )

            return True
        
        return False

    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, 
                         record_id: str = None):
        
        if not await self.is_collection_existed(collection_name):
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        try:
            _ = self.client.upsert(
                collection_name=collection_name,
                records=[
                    models.PointStruct(
                        id = record_id,
                        vector=vector,
                        payload={
                            "text": text, "metadata": metadata
                        }
                    )
                ]
            )
        except Exception as e:
            self.logger.error(f"Error while inserting batch: {e}")
            return False

        return True
    

    async def insert_many(self,collection_name: str,
                        texts: list,
                        vectors: list,
                        metadata: list = None,
                        record_ids: list = None,
                        batch_size: int = 50):

        
        if metadata is None:
            metadata = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(len(texts)))

        for i in range(0, len(texts), batch_size):

            batch_texts = texts[i:i + batch_size]
            batch_vectors = vectors[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            batch_records = record_ids[i:i + batch_size]

            batch_points = [
                models.PointStruct(
                    id=batch_records[x],
                    vector={
                        "dense": batch_vectors[x],
                        "sparse": models.Document(
                            text=batch_texts[x],
                            model="Qdrant/bm25"
                        )
                    },

                    payload={
                        "text": batch_texts[x],
                        "metadata": batch_metadata[x]
                    }
                )
                for x in range(len(batch_texts))
            ]

            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=batch_points,
                )

            except Exception as e:
                self.logger.error(
                    f"Error while inserting batch: {e}"
                )
                return False

        return True

    async def search_by_vector(
        self,
        collection_name: str,
        vector: list,
        limit: int = 5,
        filters: dict | None = None,
    ) -> List[RetrievedDocument]:

        if vector and isinstance(vector[0], list):
            vector = vector[0]

        query_filter = None

        if filters:
            conditions = []

            for key, value in filters.items():

                if key not in FILTERABLE_METADATA:
                    continue

                if isinstance(value, list):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=models.MatchAny(
                                any=[str(v) for v in value]
                            ),
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(
                                value=str(value)
                            ),
                        )
                    )

            if conditions:
                query_filter = Filter(
                    must=conditions
                )

        responses = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            using="dense",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        if not responses.points:
            return []

        return [
            RetrievedDocument(
                score=point.score,
                text=(
                    point.payload.get("text")
                    if point.payload
                    else None
                ),
                source=(
                    point.payload.get("source")
                    if point.payload
                    else None
                ),
                page=(
                    point.payload.get("page")
                    if point.payload
                    else None
                ),
                file_url=(
                    point.payload.get("file_url")
                    if point.payload
                    else None
                ),
            )
            for point in responses.points
        ]
       

    async def search_by_keyword(
        self,
        collection_name: str,
        query: str,
        limit: int,
        filters: dict | None = None,
    ) -> List[RetrievedDocument]:

        query_filter = None

        if filters:
            conditions = []

            for key, value in filters.items():

                if key not in FILTERABLE_METADATA:
                    continue

                if isinstance(value, list):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=models.MatchAny(
                                any=[str(v) for v in value]
                            ),
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(
                                value=str(value)
                            ),
                        )
                    )

            if conditions:
                query_filter = Filter(
                    must=conditions
                )

        responses = self.client.query_points(
            collection_name=collection_name,
            query=models.Document(
                text=query,
                model="Qdrant/bm25",
            ),
            using="sparse",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        if not responses.points:
            return []

        return [
            RetrievedDocument(
                score=point.score,
                text=(
                    point.payload.get("text")
                    if point.payload
                    else None
                ),
                source=(
                    point.payload.get("source")
                    if point.payload
                    else None
                ),
                page=(
                    point.payload.get("page")
                    if point.payload
                    else None
                ),
                file_url=(
                    point.payload.get("file_url")
                    if point.payload
                    else None
                ),
            )
            for point in responses.points
        ]

    def arabic_to_english_digits(
        self,
        text: str
    ) -> str:

        translation_table = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789"
        )

        return text.translate(translation_table)

    async def search_by_numeric(
        self,
        collection_name: str,
        query: str,
        limit: int,
        filters: dict | None = None,
    ) -> List[RetrievedDocument]:

        # Normalize Arabic digits in query
        normalized_query = self.arabic_to_english_digits(
            query
        )

        # Extract numeric tokens
        numbers = re.findall(
            r"(?<!\d)\d+(?!\d)",
            normalized_query
        )

        if not numbers:
            return []

        # Build Qdrant metadata filter
        query_filter = None

        if filters:
            conditions = []

            for key, value in filters.items():

                if key not in FILTERABLE_METADATA:
                    continue

                if isinstance(value, list):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=models.MatchAny(
                                any=[str(v) for v in value]
                            ),
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(
                                value=str(value)
                            ),
                        )
                    )

            if conditions:
                query_filter = Filter(
                    must=conditions
                )

        # Get documents matching metadata filters
        records = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=query_filter,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )[0]

        if not records:
            return []

        ranked_results = []

        for record in records:

            payload = record.payload or {}

            document = payload.get("text")

            if not document:
                continue

            # Normalize Arabic digits inside document
            normalized_document = (
                self.arabic_to_english_digits(
                    document
                )
            )

            score = 0

            # Check every number from query
            for number in numbers:

                pattern = (
                    rf"(?<!\d)"
                    rf"{re.escape(number)}"
                    rf"(?!\d)"
                )

                if re.search(
                    pattern,
                    normalized_document
                ):
                    score += 1

            # Keep only documents containing
            # at least one requested number
            if score > 0:
                ranked_results.append(
                    (
                        record,
                        score,
                    )
                )

        # Highest number of matches first
        ranked_results.sort(
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            RetrievedDocument(
                text=record.payload.get("text"),
                score=float(score),
                source=record.payload.get("source"),
                page=record.payload.get("page"),
                file_url=record.payload.get("file_url"),
            )
            for record, score in ranked_results[:limit]
        ]
        