from fastapi import FastAPI
from helpers import get_settings
from routes import base_router, data_router, nlp_router, user_router, agent_execution_router
from helpers import get_settings
from stores import LLMProviderFactory, VectorDBProviderFactory, RerankerProviderFactory, VisionFactory
from stores.llm.templates import TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from fastapi.middleware.cors import CORSMiddleware

from stores.llm.LLMResilienceFactory import LLMResilienceFactory

from utils.metrics import setup_metrics

from stores.tracing.TracingConfig import setup_tracing
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


app = FastAPI()

# OpenTelemetry Tracing
setup_tracing()

FastAPIInstrumentor.instrument_app(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
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
    resilience_factory = LLMResilienceFactory(provider_factory=llm_provider_factory, settings=settings)
    vectordb_provider_factory = VectorDBProviderFactory(
        config=settings,
        db_client=app.db_client
    )

    # Generation client
    app.generation_client = resilience_factory.create(
        backend=settings.GENERATION_BACKEND,
        model=settings.GENERATION_MODEL_ID,
        fallbacks=settings.GENERATION_FALLBACKS,
        client_type="generation",
    )

    # ligthweigth client
    app.ligthweigth_client = resilience_factory.create(
        backend=settings.LIGHTWEIGHT_GENERATION_BACKEND,
        model=settings.LIGHTWEIGHT_GENERATION_MODEL,
        fallbacks=settings.LIGHTWEIGHT_FALLBACKS,
        client_type="generation",
    )

    # OCR client
    app.ocr_client = llm_provider_factory.create(
        provider=settings.OCR_BACKEND
    )
    app.ocr_client.set_generation_model(
        model_id=settings.OCR_MODEL_ID
    )

    # Embedding client
    app.embedding_client = resilience_factory.create(
        backend=settings.EMBEDDING_BACKEND,
        model=settings.EMBEDDING_MODEL_ID,
        fallbacks=settings.EMBEDDING_FALLBACKS,
        client_type="embedding",
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

    # reranker client
    reranker_provider_factory = RerankerProviderFactory(
        config=settings
    )
    app.reranker_client = reranker_provider_factory.create(
        provider=settings.RERANKER_BACKEND
    )

    # vision client
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
app.include_router(user_router)
app.include_router(agent_execution_router)



