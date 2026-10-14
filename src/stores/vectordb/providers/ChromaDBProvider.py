from ..VectorDBInterface import VectorDBInterface
from stores.vectordb.VectorDBEnums import DistanceMethodEnums
from chromadb import PersistentClient
from models.db_schemes import RetrievedDocument
from rank_bm25 import BM25Okapi
from controllers.enums.nlp import NLPControllerEnums
import logging
from typing import List
import uuid
import re

class ChromaDBProvider(VectorDBInterface):

     def __init__(self, db_client: str, default_vector_size: int=786, 
                     distance_method : str = None, index_threshold: int=100):

        self.client = None
        self.db_client = db_client
        self.distance_method = distance_method
        self.default_vector_size = default_vector_size

        self.logger = logging.getLogger("uvicorn")


        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = DistanceMethodEnums.COSINE.value

        if distance_method == DistanceMethodEnums.IP.value:
            self.distance_method = DistanceMethodEnums.IP.value

     async def connect(self):
        self.client = PersistentClient(path=self.db_client)

     async def disconnect(self):
        self.client = None

     async def is_collection_existed(self, collection_name: str) -> bool:

        try:
            self.client.get_collection(name=collection_name)
            return True
        except Exception as e:
            self.logger.error(f"The collection name does not exist in Chromadb {e}")
            return False

     async def list_all_collections(self) -> List:
         return self.client.list_collections()

    
     async def get_collection_info(self, collection_name: str) -> dict:

        if not await self.is_collection_existed(collection_name=collection_name):
            self.logger.error("The collection name does not exist in Chromadb")
            return False

        collection = self.client.get_collection(name=collection_name)

        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata,
        }
    
     async def delete_collection(self, collection_name: str) -> bool:

        if await self.is_collection_existed(collection_name=collection_name):
            self.logger.info(f"Deleting collection : {collection_name}")
            self.client.delete_collection(name=collection_name)
            return True

        return False

     async def create_collection(self, collection_name: str,
                                        embedding_size: int = None,
                                        do_reset: bool = False):

        if do_reset:
            await self.delete_collection(collection_name=collection_name)

        if not await self.is_collection_existed(collection_name=collection_name):

            self.client.create_collection(
               name=collection_name,
               metadata = {
                   "hnsw:space": self.distance_method
               }
            )

            return True

        return False

     
     async def insert_one(self, collection_name: str,
                                    text: str,
                                    vector: list,
                                    metadata: dict = None,
                                    record_id: str = None):
        

        if not await self.is_collection_existed(collection_name):
            self.logger.error(
                f"Cannot insert record into non-existent collection "
                f"{collection_name}"
            )

            return False

        try:
            collection = self.client.get_collection(name=collection_name)


            collection.add(
                ids =[record_id if record_id is not None else str(hash(text))],
                embeddings=[vector],
                documents=[text],
                metadatas=[metadata if metadata is not None else {}],

            )

            return True

        except Exception as e:

            self.logger.error(
                f"Error while inserting record: {e}"
            )

            return False


     async def insert_many(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: list = None,
        record_ids: list = None,
        batch_size: int = 50
    ):

        if not await self.is_collection_existed(collection_name):

            self.logger.error(
                f"Cannot insert records into non-existent collection "
                f"{collection_name}"
            )

            return False

        if metadata is None:
            metadata = [{} for _ in texts]

        record_ids = [str(record_id) for record_id in record_ids]

        try:

            collection = self.client.get_collection(
                name=collection_name
            )

            for i in range(0, len(texts), batch_size):

                batch_texts = texts[i : i + batch_size]
                batch_vectors = vectors[i : i + batch_size]
                batch_metadata = metadata[i : i + batch_size]
                batch_ids = record_ids[i : i + batch_size]

                collection.add(
                    ids=batch_ids,
                    embeddings=batch_vectors,
                    documents=batch_texts,
                    metadatas=batch_metadata
                )

            return True

        except Exception as e:

            self.logger.error(
                f"Error while inserting batch: {e}"
            )

            return False


     def _build_chroma_filters(
        self,
        filters: dict | None,
    ) -> dict | None:

        if not filters:
            return None

        conditions = []

        for key, value in filters.items():

            if key not in NLPControllerEnums.FILTERABLE_METADATA.value:
                continue

            if isinstance(value, list):
                conditions.append({
                    key: {
                        "$in": value
                    }
                })
            else:
                conditions.append({
                    key: {
                        "$eq": value
                    }
                })

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return {
            "$and": conditions
        }

     async def search_by_vector(
        self,
        collection_name: str,
        vector: list,
        limit: int,
        filters: dict | None = None,
    ) -> List[RetrievedDocument]:

        collection = self.client.get_collection(
            name=collection_name
        )

        # Keep only allowed metadata filters
        where_filter = self._build_chroma_filters(filters)

        results = collection.query(
            query_embeddings=[vector],
            n_results=limit,
            where=where_filter,
        )

        if not results or not results.get("documents"):
            return []

        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]

        return [
            RetrievedDocument(
                text=document,
                score=1 - distance,
                source=metadata.get("source"),
                page=metadata.get("page"),
                file_url=metadata.get("file_url"),
            )
            for document, distance, metadata
            in zip(documents, distances, metadatas)
        ]

     async def search_by_keyword(
        self,
        collection_name: str,
        query: str,
        limit: int,
        filters: dict | None = None,
    ) -> List[RetrievedDocument]:

        collection = self.client.get_collection(
            name=collection_name
        )

        where_filter = self._build_chroma_filters(filters)

        results = collection.get(
            where=where_filter,
            include=["documents", "metadatas"],
        )

        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        if not documents:
            return []

        # Tokenize documents
        tokenized_documents = [
            document.split()
            for document in documents
        ]

        # BM25
        bm25 = BM25Okapi(tokenized_documents)

        query_tokens = query.split()

        scores = bm25.get_scores(query_tokens)

        # Rank documents
        ranked_results = sorted(
            zip(documents, scores, metadatas),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            RetrievedDocument(
                text=document,
                score=float(score),
                source=metadata.get("source"),
                page=metadata.get("page"),
                file_url=metadata.get("file_url"),
            )
            for document, score, metadata
            in ranked_results[:limit]
        ]

     def arabic_to_english_digits(self, text: str) -> str:
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

        collection = self.client.get_collection(
            name=collection_name
        )

        # Extract numeric tokens from query
        normalized_query = self.arabic_to_english_digits(query)

        numbers = re.findall(
            r"(?<!\d)\d+(?!\d)",
            normalized_query
        )

        if not numbers:
            return []

        # Metadata filters
        if filters:
            filters = {
                key: value
                for key, value in filters.items()
                if key in NLPControllerEnums.FILTERABLE_METADATA.value
            }

        results = collection.get(
            where=filters if filters else None,
            include=["documents", "metadatas"],
        )

        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        if not documents:
            return []

        ranked_results = []

        for document, metadata in zip(documents, metadatas):

            score = 0

            # Normalize Arabic digits inside document
            normalized_document = self.arabic_to_english_digits(
                document
            )

            for number in numbers:

                pattern = rf"(?<!\d){re.escape(number)}(?!\d)"

                if re.search(pattern, normalized_document):
                    score += 1

            if score > 0:
                ranked_results.append(
                    (
                        document,
                        score,
                        metadata,
                    )
                )

        # Highest number of matches first
        ranked_results.sort(
            key=lambda x: x[1],
            reverse=True
        )

        return [
            RetrievedDocument(
                text=document,
                score=float(score),
                source=metadata.get("source"),
                page=metadata.get("page"),
                file_url=metadata.get("file_url"),
            )
            for document, score, metadata in ranked_results[:limit]
        ]