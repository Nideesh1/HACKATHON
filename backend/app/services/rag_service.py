import json
import aiofiles
from typing import Optional, AsyncIterator

from app.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.document_service import load_metadata
from app.services.llm_service import get_llm_service


async def get_chunk_text(doc_id: str, chunk_index: int) -> Optional[str]:
    """Get chunk text by doc_id and chunk_index."""
    chunks_path = settings.documents_dir / f"{doc_id}_chunks.json"
    if not chunks_path.exists():
        return None

    async with aiofiles.open(chunks_path, "r") as f:
        content = await f.read()
        chunks = json.loads(content)

    if chunk_index >= len(chunks):
        return None

    return chunks[chunk_index]


async def retrieve(query: str, top_k: int = None) -> list[dict]:
    """Retrieve relevant chunks for a query."""
    top_k = top_k or settings.top_k

    # Search for similar chunks
    results = get_embedding_service().search(query, top_k)

    if not results:
        return []

    # Get metadata for context
    metadata = await load_metadata()

    # Build response with chunk text
    retrieved = []
    for doc_id, chunk_idx, distance in results:
        chunk_text = await get_chunk_text(doc_id, chunk_idx)
        if chunk_text:
            doc_meta = metadata.get(doc_id, {})
            retrieved.append({
                "doc_id": doc_id,
                "filename": doc_meta.get("filename", "unknown"),
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "distance": distance,
            })

    return retrieved


def build_context(chunks: list[dict]) -> str:
    """Build context string from retrieved chunks."""
    if not chunks:
        return "No relevant documents found."
    return "\n\n---\n\n".join(
        f"[{c['filename']}]: {c['text']}" for c in chunks
    )


async def query_rag(query: str, top_k: int = None, use_llm: bool = True) -> dict:
    """Full RAG query - retrieve chunks and optionally generate answer."""
    chunks = await retrieve(query, top_k)
    context = build_context(chunks)

    result = {
        "query": query,
        "retrieved_chunks": chunks,
        "context": context,
    }

    if use_llm and chunks:
        llm = get_llm_service()
        try:
            answer = await llm.generate(query, context)
            result["answer"] = answer
        except Exception as e:
            result["answer"] = f"LLM error: {str(e)}"
            result["llm_error"] = True

    return result


async def query_rag_stream(query: str, top_k: int = None) -> AsyncIterator[dict]:
    """Stream RAG response - yields chunks then streams LLM answer."""
    chunks = await retrieve(query, top_k)
    context = build_context(chunks)

    # First yield the retrieved chunks
    yield {
        "type": "chunks",
        "query": query,
        "retrieved_chunks": chunks,
        "context": context,
    }

    # Then stream the LLM answer
    if chunks:
        llm = get_llm_service()
        try:
            async for token in llm.generate_stream(query, context):
                yield {
                    "type": "token",
                    "token": token,
                }
            yield {"type": "done"}
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
            }
