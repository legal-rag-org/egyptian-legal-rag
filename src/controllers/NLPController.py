from .BaseController import BaseController
from models import Project, Chunk
from models.db_schemes.insurance_rag.schemes import Message
from typing import List
from stores.llm.LLMEnums import DocumentTypeEnum
from stores.vectordb.VectorDBEnums import PgVectorTableSchemeEnums
import logging
from models.db_schemes import RetrievedDocument
from services.MetadataFilterExtractor import MetadataFilterExtractor
from services.SummaryMemory import SummaryMemory
from .enums.nlp import NLPControllerEnums
from services.PromptInjuction import PromptInjectionDetector

from services.AgentService import AgentContext, AgentService
from tools.ToolRegistry import ToolRegistry
from tools.healthcare.HealthcareTool import HealthcareTool
from tools.rag.RAGTool import RAGTool


from fastapi import UploadFile
import tempfile
from pathlib import Path

class NLPController(BaseController):

    def __init__(self, vectordb_client, 
                       generation_client,
                       embedding_client,
                       template_parser,
                       reranker_client,
                       message_model,
                       conversation_model,
                       lightweight_client,
                       vision_client):
        
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.reranker_client = reranker_client
        self.message_model = message_model
        self.conversation_model = conversation_model
        self.lightweight_client=lightweight_client
        self.vision_client = vision_client

        self.summary_model = SummaryMemory(
            generation_client=self.lightweight_client,
            template_parser=self.template_parser
        )
        self.prompt_injection_detector = PromptInjectionDetector(
            generation_client=self.lightweight_client,
            template_parser=self.template_parser
        )

        self.metadata_filter_extractor = MetadataFilterExtractor(
            generation_client=self.lightweight_client,
            template_parser=self.template_parser,
        )

        tool_registry = ToolRegistry()

        rag_tool = RAGTool()
        healthcare_tool = HealthcareTool()

        tool_registry.register(rag_tool)
        tool_registry.register(healthcare_tool)

        self.agent_service = AgentService(
            llm=self.generation_client,
            tool_registry=tool_registry,
        )

        self.rag_tool = rag_tool

        self.rag_tool.set_rag_handler(
            self.answer_rag_questions
        )
        self.logger = logging.getLogger("uvicorn")


    def create_collection_name(self, project_id: str):
        return f"{PgVectorTableSchemeEnums._PREFIX.value}_collection_{self.vectordb_client.default_vector_size}_{project_id}"

    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(
            project_id=project.project_id
        )

        return await self.vectordb_client.delete_collection(
            collection_name=collection_name
        )

    async def get_vector_collection_info(self, project: Project):
        collection_name = self.create_collection_name(
                    project_id=project.project_id
                )

        collection_info = await self.vectordb_client.get_collection_info(
            collection_name=collection_name
        )
        return collection_info


    async def index_into_vector_db(
        self, project: Project,
        chunks: List[Chunk],
        do_reset: bool=False,
        chunks_ids: List[int] | None= None
    ):


        # 1) get collection name
        collection_name = self.create_collection_name(
            project_id=project.project_id
        )

        # 2) manage items
        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors = self.embedding_client.embed_text(
                text=texts,
                document_type=DocumentTypeEnum.DOCUMENT.value
            )

        if any(vector is None for vector in vectors):
            self.logger.error(
                "Embedding failed for one or more chunks — check the "
                "embedding backend/API key before indexing."
            )
            return False

        # 3) create collection if not exists
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset
        )


        # 4) insert into vector db
        is_inserted = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            vectors=vectors,
            metadata=metadata,
            record_ids=chunks_ids
        )

        return is_inserted


    async def search_vector_db_collection(
        self,
        project: Project, 
        text: str, 
        limit: int = 10
    ):

        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: get text embedding vector
        query_vector = self.embedding_client.embed_text(text=text, 
                                                 document_type=DocumentTypeEnum.QUERY.value)


        if not query_vector or len(query_vector) == 0:
            return False

        # step3: do semantic search
        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector= query_vector,
            limit=limit
        )

        if not results:
            return False

        return results

    def validate_metadata_filters(
        self,
        filters: dict,
        allowed_values: dict,
    ) -> dict:

        if not isinstance(filters, dict):
            return {}

        validated_filters = {}

        for field, value in filters.items():

            if field not in allowed_values:
                return {}

            allowed = allowed_values[field]

            # Single value
            if isinstance(value, str):
                if value not in allowed:
                    return {}

                validated_filters[field] = value

            # Multiple values
            elif isinstance(value, list):
                if not value:
                    return {}

                if not all(
                    isinstance(item, str) and item in allowed
                    for item in value
                ):
                    return {}

                validated_filters[field] = value

            else:
                return {}

        return validated_filters

    async def search_hybrid(
        self,
        project: Project,
        text: str,
        limit: int = 20
    ):

        
        collection_name = self.create_collection_name(
            project_id=project.project_id
        )


        query_vector = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )

        if not query_vector:
            return [], {}
        
        #step3: extract metadata filters from user query
        filters = self.metadata_filter_extractor.extract(
            query=text,
            available_fields=NLPControllerEnums.FILTERABLE_METADATA.value,
        )

        filters = self.validate_metadata_filters(
            filters=filters,
            allowed_values=NLPControllerEnums.ALLOWED_METADATA_VALUES.value,
        )

        

        vector_results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=query_vector,
            limit=limit,
            filters=filters
        )

        keyword_results = await self.vectordb_client.search_by_keyword(
            collection_name=collection_name,
            query=text,
            limit=limit,
            filters=filters
        )

        numeric_results = await self.vectordb_client.search_by_numeric(
            collection_name=collection_name,
            query=text,
            limit=limit,
            filters=filters,
        )

        # double check on return status
        vector_results = vector_results or []
        keyword_results = keyword_results or []
        numeric_results = numeric_results or []

        merged_results = self.merge_results(
            vector_results=vector_results,
            keyword_results=keyword_results,
            numeric_results=numeric_results,
            limit=limit,
        )

        return merged_results, filters

    def merge_results(
            self,
            vector_results: List[RetrievedDocument],
            keyword_results: List[RetrievedDocument],
            numeric_results: List[RetrievedDocument],
            limit: int = 20,
            k: int = 60
        ) -> List[RetrievedDocument]:
    
            scores = {}
            documents = {}
    
            for rank, document in enumerate(vector_results, start=1):
    
                document_id = document.text
    
                documents[document_id] = document
    
                scores[document_id] = scores.get(
                    document_id,
                    0
                ) + (1 / (k + rank))
    
            for rank, document in enumerate(keyword_results, start=1):
    
                document_id = document.text
    
                documents[document_id] = document
    
                scores[document_id] = scores.get(
                    document_id,
                    0
                ) + (1 / (k + rank))

            for rank, document in enumerate(numeric_results, start=1):

                document_id = document.text

                documents[document_id] = document

                scores[document_id] = scores.get(
                    document_id,
                    0,
                ) + (1 / (k + rank))
    
            ranked_documents = sorted(
                documents.items(),
                key=lambda x: scores[x[0]],
                reverse=True
            )
    
            return [
                documents[document_id]
                for document_id, _ in ranked_documents[:limit]
            ]

    def build_document_citation(self, document: RetrievedDocument) -> dict:
        if not document.file_url:
            return {
                "source": document.source,
                "page": document.page,
                "url": None,
                "label": (
                    f"📄 {document.source}"
                    f" — ص. {document.page}"
                    if document.page
                    else f"📄 {document.source}"
                ),
            }

        url = document.file_url

        if document.page:
            url = f"{url}#page={document.page}"

        return {
            "source": document.source,
            "page": document.page,
            "url": url,
            "label": (
                f"📄 {document.source}"
                f" — ص. {document.page}"
            ),
        }


    async def answer_rag_questions(self, project: Project,
                                         query: str,
                                         limit: int=10,
                                         retrieval_limit: int = 20,
                                         chat_history: list | None = None):

        if chat_history is None:
            chat_history = []


        answer, full_prompt = None, None

        # 1) retrieve related documents
        retrieved_documents, filters = await self.search_hybrid(
            project=project,
            text=query,
            limit=retrieval_limit
        )

        if not retrieved_documents or len(retrieved_documents) == 0:
            answer = NLPControllerEnums.NO_AVAILABLE_DOCUMENT_ANSWER.value
            
            return answer, full_prompt, chat_history, [], filters, []


        # 2) Rerank retrieved documents
        reranked_documents = self.reranker_client.rerank(
            query=query,
            documents=retrieved_documents
        )

        if not reranked_documents or len(reranked_documents) == 0:
            return answer, full_prompt, chat_history, [], filters, []

        # 3) Keep only the top-k reranked documents
        retrieved_documents = reranked_documents[:limit]

        # 4) Build citations
        citations = [
            self.build_document_citation(doc)
            for doc in retrieved_documents
        ]

        # 4) construct the llm prompt
        system_prompt = self.template_parser.get(
            group="rag",
            key="system_prompt",
        )

        documents_prompts = "\n".join([self.template_parser.get(
            group="rag",
            key="document_prompt",
            vars={
                "doc_num":idx + 1,
                "chunk_text": doc.text,
                "chunk_metadata": "\n".join([
                    f"المصدر: {doc.source}",
                    f"الصفحة: {doc.page}",
                    f"اللينك : {doc.file_url}"
                ]),
            }
        )  for idx, doc in  enumerate(retrieved_documents)])

        footer_prompt = self.template_parser.get(
            group="rag",
            key="footer_prompt",
            vars={
                "query" : query
            }
        )

        system_message = self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value
        )

        chat_history = [system_message] + chat_history


        full_prompt = "\n\n".join([
            documents_prompts,
            footer_prompt
        ])


        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,

        )


        self.logger.info(f"Generated answer: {answer!r}")

        return answer, full_prompt, chat_history, retrieved_documents, filters, citations


    def build_chat_history(self, messages: list):
    
        chat_history = []

        for message in messages:

            if message.role == "user":
                role = self.generation_client.enums.USER.value

            elif message.role == "assistant":
                role = self.generation_client.enums.ASSISTANT.value

            else:
                continue

            chat_history.append(
                self.generation_client.construct_prompt(
                    prompt=message.content,
                    role=role
                )
            )

        return chat_history

    def build_rewrite_history(self, messages: list) -> str:

        history = []

        for message in messages:

            history.append(
                f"{message.role}: {message.content}"
            )

        return "\n".join(history)


    
    async def extract_image_context(
        self,
        image: UploadFile,
    ) -> str:
        suffix = Path(image.filename or "").suffix or ".png"
        image_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:
                image_path = Path(temp_file.name)
                temp_file.write(await image.read())

            return await self.vision_client.extract_text_from_image(
                image=str(image_path),
            )

        finally:
            if image_path is not None:
                image_path.unlink(missing_ok=True)



    async def _build_query_with_vision(self, query: str, image: UploadFile | None) -> str:
        if not image:
            return query

        vision_context = await self.extract_image_context(image=image)

        if not vision_context:
            return query

        self.logger.info(f"Generated description {vision_context}")

        return f"""
            سؤال المستخدم:
            {query}

            محتوى الصورة:
            {vision_context}
            """.strip()


    async def _rewrite_query(self, rewrite_query: str, rewrite_history, previous_summary: str) -> str:
        query_rewriter_prompt = self.template_parser.get(
            group="rag",
            key="query_rewriter_prompt",
            vars={
                "chat_history": rewrite_history,
                "previous_summary": previous_summary,
                "query": rewrite_query,
            }
        )

        rewritten_query = self.lightweight_client.generate_text(
            prompt=query_rewriter_prompt,
            chat_history=[]
        )

        return (rewritten_query or rewrite_query).strip()


    def _detect_injection(self, query: str) -> dict:
        return self.prompt_injection_detector.detect(query=query)
    
    async def answer_chat_question(
        self,
        project: Project,
        conversation,
        query: str,
        image: UploadFile | None = None,
        limit: int = 10,
        retrieval_limit: int = 20,
        latitude: float | None = None,
        longitude: float | None = None
    ):
        

        rewrite_query = await self._build_query_with_vision(query=query, image=image)

        injection_result = self._detect_injection(rewrite_query)

        if injection_result["is_injection"]:
            self.logger.warning("Prompt injection detected: %s", injection_result.get("reason"))
            return (
                NLPControllerEnums.PORMPT_INJUCTED_ANSWER.value,
                None, [], [], query, {}, []
            )


        # 1. Load previous messages
        messages = await self.message_model.get_messages_by_conversation_id(
            conversation_id=conversation.conversation_id,
        )

        # 2. Get previous conversation summary
        previous_summary = conversation.summary or ""

        # 3. Convert DB messages to LLM chat history
        chat_history = self.build_chat_history(
            messages=messages
        )


        # For query rewriting
        rewrite_history = self.build_rewrite_history(
            messages=messages
        )

        rewritten_query = await self._rewrite_query(rewrite_query=rewrite_query, rewrite_history=rewrite_history, previous_summary=previous_summary)


        context = AgentContext(
            project=project,
            chat_history=chat_history,
            limit=limit,
            retrieval_limit=retrieval_limit,
            latitude=latitude,
            longitude=longitude,
        )
        

        # 4. Run RAG
        agent_result = await self.agent_service.run(
            query=rewritten_query,
            context=context
        )
        answer = agent_result["answer"]
        full_prompt = agent_result["full_prompt"]
        retrieved_documents = agent_result["retrieved_documents"]
        filters = agent_result["filters"]
        citations = agent_result["citations"]

        if not answer:
            return answer, full_prompt, retrieved_documents, chat_history, rewritten_query, filters, citations

        # 5. Save user message
        user_message = Message(
            role=self.generation_client.enums.USER.value,
            content=query,
            message_conversation_id=conversation.conversation_id
        )

        await self.message_model.insert_message(
            message=user_message
        )

        # 6. Save assistant message
        assistant_message = Message(
            role=self.generation_client.enums.ASSISTANT.value,
            content=answer,
            message_conversation_id=conversation.conversation_id
        )

        await self.message_model.insert_message(
            message=assistant_message
        )

        # 7. Load messages again after saving the new turn
        updated_messages = (
            await self.message_model.get_messages_by_conversation_id(
                conversation_id=conversation.conversation_id,
            )
        )

        # 8. Check if it's time to generate a new summary
        message_count = len(updated_messages)

        if message_count > 0 and message_count % 6 == 0:

            # Get only the latest 6 messages
            recent_messages = updated_messages[-6:]

            # Convert recent messages to text
            recent_history = self.build_rewrite_history(
                messages=recent_messages
            )

            # 9. Generate updated rolling summary
            new_summary = self.summary_model.summarize(
                conversation=recent_history,
                previous_summary=previous_summary
            )

            # 10. Save the updated summary
            await self.conversation_model.update_summary(
                conversation_id=conversation.conversation_id,
                summary=new_summary
            )


        return answer, full_prompt, retrieved_documents, chat_history, rewritten_query, filters, citations