from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"
    documents_dir: Path = data_dir / "documents"
    embeddings_dir: Path = data_dir / "embeddings"
    models_dir: Path = data_dir / "models"

    # Whisper settings
    whisper_model: str = "base"  # tiny, base, small, medium, large

    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1024  # Larger chunks for complete claims
    chunk_overlap: int = 50

    # RAG settings
    top_k: int = 5  # Retrieve more chunks for better coverage

    # LLM settings (local GGUF model via llama-cpp-python)
    llm_model_repo: str = "google/gemma-3-4b-it-qat-q4_0-gguf"
    llm_model_file: str = "gemma-3-4b-it-q4_0.gguf"
    llm_mmproj_file: str = "mmproj-model-f16-4B.gguf"  # Multimodal projection for vision
    llm_context_size: int = 4096
    llm_threads: int = 4  # Adjust based on CPU cores

    # Router model (FunctionGemma for intent classification)
    router_model: str = "google/functiongemma-270m-it"

    class Config:
        env_prefix = "RAG_"


settings = Settings()

# Ensure directories exist
settings.documents_dir.mkdir(parents=True, exist_ok=True)
settings.embeddings_dir.mkdir(parents=True, exist_ok=True)
settings.models_dir.mkdir(parents=True, exist_ok=True)
