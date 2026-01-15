import os
import uuid
import json
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional
import platform

# Fix for PyTorch/OpenMP crash on Apple Silicon (harmless on Windows/Linux)
if platform.system() == "Darwin":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")

from chonkie import NeuralChunker

from app.config import settings
from app.models.schemas import DocumentMetadata

# Lazy-loaded chunker
_chunker: Optional[NeuralChunker] = None


def get_chunker() -> NeuralChunker:
    """Get or create neural chunker for topic detection."""
    global _chunker
    if _chunker is None:
        print("[Chunker] Initializing NeuralChunker (BERT-based topic detection)")
        _chunker = NeuralChunker(
            model="mirth/chonky_modernbert_base_1",
            device_map="cpu",
            min_characters_per_chunk=50,
        )
    return _chunker


def get_metadata_path() -> Path:
    return settings.embeddings_dir / "metadata.json"


async def load_metadata() -> dict:
    path = get_metadata_path()
    if not path.exists():
        return {}
    async with aiofiles.open(path, "r") as f:
        content = await f.read()
        return json.loads(content) if content else {}


async def save_metadata(metadata: dict) -> None:
    path = get_metadata_path()
    async with aiofiles.open(path, "w") as f:
        await f.write(json.dumps(metadata, default=str, indent=2))


def chunk_text(text: str) -> list[str]:
    """Split text into chunks using neural topic detection."""
    chunker = get_chunker()
    chunks = chunker(text)

    # Extract text and log
    result = [chunk.text.strip() for chunk in chunks if chunk.text.strip()]
    print(f"[Chunker] Created {len(result)} neural chunks (topic-based)")
    for i, chunk in enumerate(result):
        preview = chunk[:100].replace('\n', ' ')
        print(f"  Chunk {i}: {preview}...")

    return result


async def save_document(filename: str, content: bytes) -> tuple[str, list[str]]:
    """Save document and return doc_id and chunks."""
    doc_id = str(uuid.uuid4())

    # Save raw file
    file_path = settings.documents_dir / f"{doc_id}.txt"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Chunk the text semantically
    text = content.decode("utf-8")
    chunks = chunk_text(text)

    # Save chunks
    chunks_path = settings.documents_dir / f"{doc_id}_chunks.json"
    async with aiofiles.open(chunks_path, "w") as f:
        await f.write(json.dumps(chunks))

    # Update metadata
    metadata = await load_metadata()
    metadata[doc_id] = {
        "id": doc_id,
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat(),
        "chunk_count": len(chunks),
        "size_bytes": len(content),
    }
    await save_metadata(metadata)

    return doc_id, chunks


async def get_document(doc_id: str) -> Optional[DocumentMetadata]:
    """Get document metadata by ID."""
    metadata = await load_metadata()
    if doc_id not in metadata:
        return None
    return DocumentMetadata(**metadata[doc_id])


async def list_documents() -> list[DocumentMetadata]:
    """List all documents."""
    metadata = await load_metadata()
    return [DocumentMetadata(**doc) for doc in metadata.values()]


async def delete_document(doc_id: str) -> bool:
    """Delete document and its chunks/embeddings."""
    metadata = await load_metadata()
    if doc_id not in metadata:
        return False

    # Delete files
    file_path = settings.documents_dir / f"{doc_id}.txt"
    chunks_path = settings.documents_dir / f"{doc_id}_chunks.json"

    if file_path.exists():
        file_path.unlink()
    if chunks_path.exists():
        chunks_path.unlink()

    # Remove from metadata
    del metadata[doc_id]
    await save_metadata(metadata)

    return True


async def get_all_chunks() -> list[tuple[str, str, int]]:
    """Get all chunks with their doc_id and chunk_index."""
    metadata = await load_metadata()
    all_chunks = []

    for doc_id in metadata:
        chunks_path = settings.documents_dir / f"{doc_id}_chunks.json"
        if chunks_path.exists():
            async with aiofiles.open(chunks_path, "r") as f:
                content = await f.read()
                chunks = json.loads(content)
                for i, chunk in enumerate(chunks):
                    all_chunks.append((doc_id, chunk, i))

    return all_chunks
