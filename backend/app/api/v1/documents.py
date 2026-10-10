"""
NEXORA AI — Document Intelligence API Endpoints
Provides endpoints for:
- POST /api/v1/documents/upload: Secure multi-format document uploads
- GET /api/v1/documents: List uploaded documents with stats
- GET /api/v1/documents/{doc_id}: Fetch document metadata and preview
- DELETE /api/v1/documents/{doc_id}: Permanently delete uploaded document
- POST /api/v1/documents/action: Run AI analysis (ask, summarize, compare, notes, quiz, etc.)
"""

from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.models.schemas import (
    DocumentItem,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentActionRequest,
    DocumentActionResponse
)
from app.services.documents.storage import document_storage
from app.services.documents.intelligence import document_intelligence
from app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentItem)
async def upload_document(
    file: UploadFile = File(...)
):
    """
    Securely uploads, parses, and indexes a user-provided file (PDF, DOCX, TXT, CSV, XLSX, PNG, JPG).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    try:
        file_bytes = await file.read()
        doc_item = document_storage.save_and_process_upload(
            file_bytes=file_bytes,
            original_filename=file.filename,
            content_type=file.content_type or "application/octet-stream"
        )
        return doc_item
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """Lists all active uploaded documents."""
    docs = document_storage.list_documents()
    return DocumentListResponse(documents=docs, total_count=len(docs))


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document_details(document_id: str):
    """Retrieves document metadata, preview text, and chunk indices."""
    doc = document_storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    preview = document_storage.get_preview_text(document_id)
    chunks = document_storage.get_chunks(document_id)

    return DocumentDetailResponse(
        document=doc,
        preview_text=preview,
        chunks=chunks[:10]  # preview first 10 chunks
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Permanently deletes document and its chunks from backend storage."""
    deleted = document_storage.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "success", "message": f"Document '{document_id}' deleted successfully."}


@router.post("/action", response_model=DocumentActionResponse)
async def execute_document_action(request: DocumentActionRequest):
    """
    Executes grounded AI analysis on one or more uploaded documents.
    Actions: ask, summarize, extract_key_points, compare, study_notes, faq, flashcards, quiz, explain_simply, extract_tables.
    """
    if not request.document_ids:
        raise HTTPException(status_code=400, detail="At least one document_id is required.")

    try:
        response = await document_intelligence.execute_action(
            document_ids=request.document_ids,
            action=request.action,
            query=request.query or "",
            provider=request.provider or "auto",
            model=request.model or "gemini-1.5-flash",
            client_api_key=request.client_api_key or "",
            temperature=request.temperature or 0.5
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")
