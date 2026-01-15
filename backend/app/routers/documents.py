from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import (
    DocumentMetadata,
    DocumentList,
    DocumentUploadResponse,
    DeleteResponse,
)
from app.services import document_service
from app.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentList)
async def list_documents():
    """List all uploaded documents."""
    docs = await document_service.list_documents()
    return DocumentList(documents=docs, total=len(docs))


@router.get("/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str):
    """Get document metadata by ID."""
    doc = await document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a .txt document."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")

    content = await file.read()

    # Save document and get chunks
    doc_id, chunks = await document_service.save_document(file.filename, content)

    # Add to embedding index
    get_embedding_service().add_document_chunks(doc_id, chunks)

    return DocumentUploadResponse(
        id=doc_id,
        filename=file.filename,
        message="Document uploaded and indexed successfully",
        chunk_count=len(chunks),
    )


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(doc_id: str):
    """Delete a document by ID."""
    # Check if exists
    doc = await document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from embedding index
    get_embedding_service().remove_document(doc_id)

    # Delete document files
    await document_service.delete_document(doc_id)

    return DeleteResponse(message="Document deleted successfully", deleted_id=doc_id)
