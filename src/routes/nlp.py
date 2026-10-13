from fastapi import APIRouter, status, Request, File, UploadFile, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from .schemes import PushRequest, SearchRequest, ChatRequest
from models import ProjectModel, ChunkModel
from models import ConversationModel, MessageModel
from controllers import NLPController
from models.Enums import ResponseSignal
import logging
from tqdm.auto import tqdm
from typing import Optional
from uuid import UUID
from models.UserModel import UserModel

from utils.auth import get_current_user

logger = logging.getLogger("uvicorn.error")


nlp_router = APIRouter(
    prefix = "/api/v1/nlp",
    tags=["api_v1", "nlp"]
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):

    project_model = await ProjectModel.create_instance(
             db_client=request.app.db_client
        )
    project = await project_model.get_project_or_create_one(project_id=project_id)

    if not project:
        return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content = {
                        "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
                    }
                )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    message_model = await MessageModel.create_instance(
            db_client=request.app.db_client
        )

    conversation_model = await ConversationModel.create_instance(
                 db_client=request.app.db_client
             )
    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker_client=request.app.reranker_client,
        message_model=message_model,
        lightweight_client=request.app.ligthweigth_client ,
        conversation_model=conversation_model,
        vision_client=request.app.vision_client 
    )

    has_records = True
    page_no = 1
    inserted_chunks_into_vdb = 0
    is_first_page = True


    # create collection if not exists
    collection_name = nlp_controller.create_collection_name(
        project_id=project.project_id
    )

    _  = await request.app.vectordb_client.create_collection(
         collection_name = collection_name,
         embedding_size = request.app.embedding_client.embedding_size,
         do_reset = push_request.do_reset
    )

    # setup batching 
    if push_request.asset_id:
        total_chunks_count = await chunk_model.get_total_chunk_count_by_asset_id(
            asset_id=push_request.asset_id
        )
    else:
        total_chunks_count = await chunk_model.get_total_chunk_count(
            project_id=project.project_id
        )
    pbar = tqdm(total=total_chunks_count, desc="vector indexing", position=0)

    while has_records:
        if push_request.asset_id:
            page_chunks = await chunk_model.get_chunks_by_asset_id(
                asset_id=push_request.asset_id,
                page_no=page_no
            )
        else:
            page_chunks = await chunk_model.get_chunks_by_project_id(
                project_id=project.project_id,
                page_no=page_no
            )

        if len(page_chunks):
            page_no += 1


        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break

        chunks_ids = [c.chunk_id for c in page_chunks]

        is_inserted = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=page_chunks,
                do_reset=push_request.do_reset and is_first_page,
                chunks_ids=chunks_ids
            )

        if not is_inserted:
            return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content = {
                            "signal": ResponseSignal.INSERT_INTO_VECTOR_DB_ERROR.value
                        }
                    )
        
        inserted_chunks_into_vdb += len(page_chunks)
        pbar.update(len(page_chunks))
        is_first_page = False


    return JSONResponse(
                    content = {
                        "signal": ResponseSignal.INSERT_INTO_VECTOR_DB_SUCCESS.value,
                        "inserted_chunks" : inserted_chunks_into_vdb
                    }
                )


@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):

    project_model = await ProjectModel.create_instance(
                 db_client=request.app.db_client
            )
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
            }
        )

    message_model = await MessageModel.create_instance(
            db_client=request.app.db_client
        )

    conversation_model = await ConversationModel.create_instance(
                 db_client=request.app.db_client
             )

    
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker_client=request.app.reranker_client,
        message_model=message_model,
        lightweight_client=request.app.ligthweigth_client,
        conversation_model=conversation_model ,
        vision_client=request.app.vision_client 
    )

    collection_info = await nlp_controller.get_vector_collection_info(
        project=project
    )

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info
        }
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int, search_request: SearchRequest):

   
   project_model = await ProjectModel.create_instance(
                    db_client=request.app.db_client
    )
   project = await project_model.get_project_or_create_one(project_id=project_id)
    
   if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {
                "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
            }
        )

   message_model = await MessageModel.create_instance(
           db_client=request.app.db_client
       )

   conversation_model = await ConversationModel.create_instance(
                db_client=request.app.db_client
            )

    
   nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.ligthweigth_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker_client=request.app.reranker_client,
        message_model=message_model,
        lightweight_client=request.app.ligthweigth_client ,
        conversation_model=conversation_model,
        vision_client=request.app.vision_client 
    )

   results, filters = await nlp_controller.search_hybrid(
        project=project,
        text=search_request.text,
        limit=search_request.reranker_limit
    )

   if not results:
        return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value
                }
            )
    
   return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [ result.dict()  for result in results ],
            "filters": filters
        }
    )

@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, search_request: SearchRequest):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    message_model = await MessageModel.create_instance(
            db_client=request.app.db_client
    )

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker_client=request.app.reranker_client,
        message_model=message_model,
        lightweight_client=request.app.ligthweigth_client,
        conversation_model=conversation_model,
        vision_client=request.app.vision_client 
    )

    answer, full_prompt, chat_history, retreived_documents, filters, citations = await nlp_controller.answer_rag_questions(
        project=project,
        query=search_request.text,
        retrieval_limit=search_request.reranker_limit,
        limit=search_request.limit
    )

    if not answer:
        return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                }
        )
    
    return JSONResponse(
    content=jsonable_encoder({
        "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
        "answer": answer,
        "full_prompt": full_prompt,
        "chat_history": chat_history,
        "retreived_documents": retreived_documents,
        "filters" : filters,
        "citations" : citations
    })
)


@nlp_router.post("/chat/{project_id}")
async def chat(
    request: Request,
    project_id: int,
    current_user = Depends(get_current_user),

    text: str = Form(...),
    conversation_uuid: Optional[UUID] = Form(None),
    limit: int = Form(10),
    reranker_limit: int = Form(20),
    title: Optional[str] = Form(None),

    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),

    image: UploadFile | None = File(None),
):

    chat_request = ChatRequest(
        text=text,
        conversation_uuid=conversation_uuid,
        limit=limit,
        reranker_limit=reranker_limit,
        title=title or "محادثة جديدة",
        latitude=latitude,
        longitude=longitude
    )

    project_model = await ProjectModel.create_instance(
    db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    message_model = await MessageModel.create_instance(
        db_client=request.app.db_client
    )

    is_new_conversation = chat_request.conversation_uuid is None

    conversation = await conversation_model.get_or_create_conversation(
        project_id=project.project_id,
        user_id=current_user.user_id,
        conversation_uuid=chat_request.conversation_uuid,
        title=chat_request.title,
    )

    if conversation is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.CONVERSATION_NOT_FOUND.value
            }
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker_client=request.app.reranker_client,
        message_model=message_model,
        lightweight_client=request.app.ligthweigth_client,
        conversation_model=conversation_model,
        vision_client=request.app.vision_client 
    )

    answer, full_prompt, retrieved_documents, chat_history, rewritten_query, filters, citations = (
        await nlp_controller.answer_chat_question(
            project=project,
            conversation=conversation,
            query=chat_request.text,
            image=image,
            retrieval_limit=chat_request.reranker_limit,
            limit=chat_request.limit,
            latitude=chat_request.latitude,
            longitude=chat_request.longitude
        )
    )

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                "filters": filters
            }
        )

    return JSONResponse(
        content=jsonable_encoder({
            "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
            "conversation_uuid": conversation.conversation_uuid,
            "answer": answer,
            "full_prompt": full_prompt,
            "retrieved_documents": retrieved_documents,
            "chat_history" : chat_history,
            "rewritten_query": rewritten_query,
            "filters": filters,
            "citations":citations
        })
    )



@nlp_router.get("/conversations/{project_id}")
async def list_conversations(
    request: Request,
    project_id: int,
    current_user = Depends(get_current_user),
    page_no: int = 1,
    page_size: int = 50,
):
    if page_no < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters.",
        )

    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    conversations = (
        await conversation_model.get_conversations_by_user_and_project(
            user_id=current_user.user_id,
            project_id=project_id,
            page_no=page_no,
            page_size=page_size,
        )
    )

    return {
        "conversations": [
            {
                "conversation_uuid": str(item.conversation_uuid),
                "title": item.title,
                "summary": item.summary,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in conversations
        ],
        "page_no": page_no,
        "page_size": page_size,
    }

@nlp_router.get("/conversations/{project_id}/{conversation_uuid}/messages")
async def get_conversation_messages(
    request: Request,
    project_id: int,
    conversation_uuid: UUID,
    current_user = Depends(get_current_user),
):


    conversation_model = await ConversationModel.create_instance(
        db_client=request.app.db_client
    )

    conversation = (
        await conversation_model.get_conversation_by_uuid_project_and_user(
            conversation_uuid=conversation_uuid,
            project_id=project_id,
            user_id=current_user.user_id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail=ResponseSignal.CONVERSATION_NOT_FOUND.value,
        )

    message_model = await MessageModel.create_instance(
        db_client=request.app.db_client
    )

    messages = await message_model.get_messages_by_conversation_id(
        conversation_id=conversation.conversation_id,
    )

    return jsonable_encoder({
        "conversation_uuid": str(conversation.conversation_uuid),
        "title": conversation.title,
        "messages": [
            {
                "role": (
                    message.role.value
                    if hasattr(message.role, "value")
                    else message.role
                ),
                "content": message.content,
            }
            for message in messages
        ],
    })