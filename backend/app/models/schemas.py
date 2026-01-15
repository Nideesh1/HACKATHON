from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    chunk_count: int
    size_bytes: int


class DocumentList(BaseModel):
    documents: list[DocumentMetadata]
    total: int


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    message: str
    chunk_count: int


class DeleteResponse(BaseModel):
    message: str
    deleted_id: str


class TranscriptionResult(BaseModel):
    text: str
    language: Optional[str] = None


class RAGQuery(BaseModel):
    query: str
    top_k: Optional[int] = 3


class RAGResult(BaseModel):
    query: str
    retrieved_chunks: list[dict]
    answer: Optional[str] = None


class WebSocketMessage(BaseModel):
    type: str  # "audio", "transcription", "rag_result", "error"
    data: dict
