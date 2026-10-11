from enum import Enum


class ResponseSignal(Enum):

    FILE_VALIDATED_SUCCESS = "file validated success"
    FILE_TYPE_NOT_SUPPORTED = "file type not supported"
    FILE_SIZE_EXCEDDED = "file size excedded"
    FILE_UPLOADED_SUCCESS = 'file uploaded success'
    FILE_UPLOADED_FAIL = 'file uploaded fail'
    FILE_PROCESSED_SUCCESS = "file_processed_success"
    FILE_PROCESSED_FAIL = "file_processed_fail"
    NO_FILES_ERROR = "no_found_files"
    FILE_ID_ERROR = "no_file_found_with_this_id"
    PROJECT_NOT_FOUND_ERROR="project_not_found_error"
    INSERT_INTO_VECTOR_DB_ERROR="insert_into_vectordb_error"
    INSERT_INTO_VECTOR_DB_SUCCESS="insert_into_vectordb_success"
    VECTORDB_COLLECTION_RETRIEVED = "vectordb_collection_retrieved"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    VECTORDB_SEARCH_SUCCESS="vectordb_search_sucess"
    COLLECTION_NOT_FOUND="collection_not_found"
    RAG_ANSWER_ERROR="rag-answer-error"
    RAG_ANSWER_SUCCESS="rag-answer-success"
    CONVERSATION_NOT_FOUND = "conversation-not-found"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    
    