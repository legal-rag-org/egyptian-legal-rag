from fastapi import FastAPI
from helpers import get_settings
from routes import base_router, data_router, nlp_router
from helpers import get_settings
from stores import LLMProviderFactory, VectorDBProviderFactory, RerankerProviderFactory, VisionFactory
from stores.llm.templates import TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from utils.metrics import setup_metrics

app = FastAPI()

setup_metrics(app=app)

@app.on_event("startup")
async def startup_span():
    settings = get_settings()

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    app.db_engine = create_async_engine(postgres_conn)

    app.db_client = sessionmaker(
        app.db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    

    llm_provider_factory = LLMProviderFactory(config=settings)
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings,
        db_client=app.db_client
    )

    # Generation client
    app.generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    app.generation_client.set_generation_model(
        model_id=settings.GENERATION_MODEL_ID
    )

    # Metadata filter client
    app.ligthweigth_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )
    app.ligthweigth_client.set_generation_model(
        model_id=settings.LIGHTWEIGHT_GENERATION_MODEL
    )

    # Embedding client
    app.embedding_client = llm_provider_factory.create(
        provider=settings.EMBEDDING_BACKEND
    )
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE
    )

    # VectorDB client
    app.vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await app.vectordb_client.connect()

    # template parser
    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG
    )

    # reranker config
    reranker_provider_factory = RerankerProviderFactory(
        config=settings
    )
    app.reranker_client = reranker_provider_factory.create(
        provider=settings.RERANKER_BACKEND
    )

    # table extractor config
    app.vision_factory = VisionFactory(
        config=settings,
        template_parser=app.template_parser,
    )
    app.vision_client = app.vision_factory.create(
        provider=settings.VISION_BACKEND
    )




@app.on_event("shutdown")
async def shutdown_span():
    await app.db_engine.dispose()
    await app.vectordb_client.disconnect()

app.include_router(base_router)
app.include_router(data_router)
app.include_router(nlp_router)



