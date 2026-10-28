from fastapi import HTTPException, status
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):

    APP_NAME: str
    APP_VERSION: str


    OPENAI_API_KEY: str

    FILE_ALLOWED_EXTENSIONS: list
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD:str
    POSTGRES_HOST:str
    POSTGRES_PORT:int
    POSTGRES_MAIN_DATABASE:str

    GENERATION_BACKEND_LITERAL: List[str]=None
    GENERATION_BACKEND: str
    LIGHTWEIGHT_GENERATION_BACKEND: str
    LIGHTWEIGHT_GENERATION_MODEL: str
    EMBEDDING_BACKEND_LITERAL: List[str]=None
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: str=None
    OPENAI_API_URL: str=None
    COHERE_API_KEY: str=None
    GEMINI_API_KEY: str=None
    GROQ_API_KEY: str=None
    OPENROUTER_API_KEY: str=None
    OPENROUTER_BASE_URL:str = "https://openrouter.ai/api/v1"
    OLLAMA_HOST: str=None

    GENERATION_MODEL_ID: str=None
    EMBEDDING_MODEL_ID: str=None
    EMBEDDING_MODEL_SIZE: int=None

    INPUT_DAFAULT_MAX_CHARACTERS: int=None
    GENERATION_DAFAULT_MAX_TOKENS: int=None
    GENERATION_DAFAULT_TEMPERATURE: float=None

    VECTOR_DB_BACKEND_LITERAL: List[str]=None
    VECTOR_DB_BACKEND: str
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: str=None
    VECTOR_DB_PGVEC_INDEX_THRESHOLD: int=500

    PRIMARY_LANG:str=None
    DEFAULT_LANG:str="en"

    RERANKER_BACKEND: str
    RERANKER_MODEL_ID: str
    RERANKER_MAX_LENGTH: int=8192

    VISION_MODEL_ID: str
    VISION_BACKEND: str


    OCR_BACKEND: str
    OCR_MODEL_ID: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file=".env"

def get_settings():
    return Settings()