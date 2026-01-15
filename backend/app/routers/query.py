from fastapi import APIRouter

from app.models.schemas import RAGQuery, RAGResult
from app.services.rag_service import query_rag

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=RAGResult)
async def query_documents(request: RAGQuery):
    """Query documents using RAG."""
    result = await query_rag(request.query, request.top_k)
    return RAGResult(
        query=result["query"],
        retrieved_chunks=result["retrieved_chunks"],
    )
