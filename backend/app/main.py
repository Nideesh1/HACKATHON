from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    print("Starting up - loading models...")

    # Load embedding model
    from app.services.embedding_service import get_embedding_service
    get_embedding_service()

    # Load whisper model
    from app.services.whisper_service import get_whisper_service
    get_whisper_service()

    # Load NeuralChunker (BERT model for topic-based chunking)
    from app.services.document_service import get_chunker
    get_chunker()

    print("All models loaded successfully!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="RAG Voice Backend",
    description="CPU-only local RAG demo with voice interface",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (import after app creation to avoid circular imports)
from app.routers import documents, voice, query

app.include_router(documents.router)
app.include_router(voice.router)
app.include_router(query.router)


@app.get("/")
async def root():
    return {
        "message": "RAG Voice Backend",
        "docs": "/docs",
        "endpoints": {
            "documents": "/documents",
            "query": "/query",
            "voice_ws": "/ws/voice",
        },
    }


@app.get("/health")
async def health():
    from app.services.embedding_service import get_embedding_service
    from app.services.llm_service import get_llm_service

    llm_ok = await get_llm_service().health_check()

    return {
        "status": "healthy" if llm_ok else "degraded",
        "index_size": get_embedding_service().get_index_size(),
        "ollama": "connected" if llm_ok else "disconnected",
    }
