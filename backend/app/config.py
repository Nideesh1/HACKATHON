from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    documents_dir: Path = data_dir / "documents"
    embeddings_dir: Path = data_dir / "embeddings"

    # Whisper settings
    whisper_model: str = "base"  # tiny, base, small, medium, large

    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1024  # Larger chunks for complete claims
    chunk_overlap: int = 50

    # RAG settings
    top_k: int = 5  # Retrieve more chunks for better coverage

    # Ollama settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"

    class Config:
        env_prefix = "RAG_"


settings = Settings()

# Ensure directories exist
settings.documents_dir.mkdir(parents=True, exist_ok=True)
settings.embeddings_dir.mkdir(parents=True, exist_ok=True)
