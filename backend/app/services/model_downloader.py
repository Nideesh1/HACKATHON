"""Download GGUF models from HuggingFace."""
import os
from pathlib import Path
from huggingface_hub import hf_hub_download
from dotenv import load_dotenv

from app.config import settings

# Load .env file if it exists
load_dotenv()


def get_hf_token() -> str | None:
    """Get HuggingFace token from environment."""
    token = os.getenv("HF_TOKEN")
    if not token or token == "your_huggingface_token_here":
        return None
    return token


def download_model() -> Path:
    """Download the LLM model if not already present."""
    model_path = settings.models_dir / settings.llm_model_file

    if model_path.exists():
        print(f"[Model] Already downloaded: {model_path}")
    else:
        token = get_hf_token()
        if not token:
            print("[Model] ERROR: HF_TOKEN not set!")
            print("[Model] Please set HF_TOKEN in backend/.env file")
            print("[Model] Get your token at: https://huggingface.co/settings/tokens")
            raise ValueError("HF_TOKEN environment variable is required for downloading gated models")

        print(f"[Model] Downloading {settings.llm_model_file} from {settings.llm_model_repo}...")
        print("[Model] This may take a few minutes (~3GB)...")

        hf_hub_download(
            repo_id=settings.llm_model_repo,
            filename=settings.llm_model_file,
            local_dir=settings.models_dir,
            local_dir_use_symlinks=False,
            token=token,
        )
        print(f"[Model] Downloaded to: {model_path}")

    return model_path


def download_mmproj() -> Path:
    """Download the multimodal projection model for vision support."""
    mmproj_path = settings.models_dir / settings.llm_mmproj_file

    if mmproj_path.exists():
        print(f"[Model] mmproj already downloaded: {mmproj_path}")
        return mmproj_path

    token = get_hf_token()
    if not token:
        print("[Model] WARNING: HF_TOKEN not set, skipping mmproj download")
        return None

    print(f"[Model] Downloading {settings.llm_mmproj_file} for vision support...")
    print("[Model] This may take a minute (~850MB)...")

    hf_hub_download(
        repo_id=settings.llm_model_repo,
        filename=settings.llm_mmproj_file,
        local_dir=settings.models_dir,
        local_dir_use_symlinks=False,
        token=token,
    )
    print(f"[Model] Downloaded to: {mmproj_path}")

    return mmproj_path


def ensure_model_exists() -> Path:
    """Ensure the model exists, downloading if necessary."""
    model_path = settings.models_dir / settings.llm_model_file

    if not model_path.exists():
        return download_model()

    return model_path


if __name__ == "__main__":
    # Allow running directly to pre-download
    download_model()
