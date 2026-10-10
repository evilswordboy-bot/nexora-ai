"""
NEXORA AI — Document Storage & In-Memory Registry
Manages user uploaded documents, raw files, parsed JSON representations,
and cached chunk indices safely on the backend.
"""

import os
import json
import uuid
import shutil
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from app.config import settings
from app.models.schemas import DocumentItem, DocumentChunk, utc_now
from app.services.documents.parsers import DocumentParser, ParsedDocument
from app.services.documents.chunker import DocumentChunker, LexicalRetriever


class DocumentStorageService:
    """Manages document lifecycle, storage, and retrieval."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or settings.document_storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        # Store in-memory cache for fast lookup
        self._doc_cache: Dict[str, DocumentItem] = {}
        self._chunks_cache: Dict[str, List[DocumentChunk]] = {}
        self._parsed_cache: Dict[str, ParsedDocument] = {}
        self._load_existing_registry()

    def _get_doc_dir(self, doc_id: str) -> Path:
        return self.storage_dir / doc_id

    def _load_existing_registry(self):
        """Discovers existing parsed documents in the storage folder."""
        for item in self.storage_dir.iterdir():
            if item.is_dir():
                meta_file = item / "meta.json"
                chunks_file = item / "chunks.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            doc_item = DocumentItem(**data)
                            self._doc_cache[doc_item.id] = doc_item

                        if chunks_file.exists():
                            with open(chunks_file, "r", encoding="utf-8") as f:
                                c_data = json.load(f)
                                self._chunks_cache[doc_item.id] = [
                                    DocumentChunk(**c) for c in c_data
                                ]
                    except Exception:
                        pass

    def save_and_process_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        content_type: str
    ) -> DocumentItem:
        """Saves file securely, parses content, and builds chunks."""
        # Sanitize filename
        safe_filename = Path(original_filename).name
        ext = Path(safe_filename).suffix.lower()

        if not DocumentParser.is_supported(safe_filename):
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: PDF, DOCX, TXT, CSV, XLSX, PNG, JPG, WEBP."
            )

        if len(file_bytes) > settings.max_upload_size_bytes:
            mb_limit = settings.max_upload_size_bytes // (1024 * 1024)
            raise ValueError(f"File size exceeds maximum permitted limit of {mb_limit}MB.")

        # Create isolated folder for document
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc_folder = self._get_doc_dir(doc_id)
        doc_folder.mkdir(parents=True, exist_ok=True)

        saved_file_path = doc_folder / f"raw{ext}"
        with open(saved_file_path, "wb") as f:
            f.write(file_bytes)

        # Parse file
        try:
            parsed = DocumentParser.parse_file(str(saved_file_path), safe_filename)
            self._parsed_cache[doc_id] = parsed

            # Chunk document
            chunker = DocumentChunker(
                target_chunk_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens
            )
            pages_dict = [p.model_dump() for p in parsed.pages]
            chunks = chunker.chunk_document(doc_id, pages_dict)
            self._chunks_cache[doc_id] = chunks

            doc_item = DocumentItem(
                id=doc_id,
                filename=safe_filename,
                original_filename=safe_filename,
                file_type=parsed.file_type,
                size_bytes=len(file_bytes),
                created_at=utc_now(),
                status="ready",
                page_count=parsed.total_pages,
                total_characters=parsed.total_characters,
                total_chunks=len(chunks),
                metadata=parsed.metadata
            )

            # Persist metadata and chunks to disk
            with open(doc_folder / "meta.json", "w", encoding="utf-8") as f:
                json.dump(doc_item.model_dump(mode="json"), f, indent=2)

            with open(doc_folder / "chunks.json", "w", encoding="utf-8") as f:
                json.dump([c.model_dump(mode="json") for c in chunks], f, indent=2)

            self._doc_cache[doc_id] = doc_item
            return doc_item

        except Exception as e:
            # Mark error status
            doc_item = DocumentItem(
                id=doc_id,
                filename=safe_filename,
                original_filename=safe_filename,
                file_type=ext.replace(".", ""),
                size_bytes=len(file_bytes),
                created_at=utc_now(),
                status="error",
                error_message=str(e)
            )
            self._doc_cache[doc_id] = doc_item
            raise RuntimeError(f"Document processing failed: {str(e)}")

    def list_documents(self) -> List[DocumentItem]:
        """Returns sorted list of documents by recency."""
        docs = list(self._doc_cache.values())
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return docs

    def get_document(self, doc_id: str) -> Optional[DocumentItem]:
        return self._doc_cache.get(doc_id)

    def get_chunks(self, doc_id: str) -> List[DocumentChunk]:
        return self._chunks_cache.get(doc_id, [])

    def get_preview_text(self, doc_id: str, max_chars: int = 1500) -> str:
        chunks = self.get_chunks(doc_id)
        if not chunks:
            return ""
        combined = "\n\n".join(c.content for c in chunks[:3])
        return combined[:max_chars]

    def delete_document(self, doc_id: str) -> bool:
        """Permanently deletes document folder and clears caches."""
        if doc_id in self._doc_cache:
            del self._doc_cache[doc_id]
        if doc_id in self._chunks_cache:
            del self._chunks_cache[doc_id]
        if doc_id in self._parsed_cache:
            del self._parsed_cache[doc_id]

        doc_folder = self._get_doc_dir(doc_id)
        if doc_folder.exists():
            shutil.rmtree(doc_folder, ignore_errors=True)
            return True
        return False

    def retrieve_relevant_passages(
        self,
        doc_ids: List[str],
        query: str,
        top_k: int = 5
    ) -> List[Tuple[DocumentChunk, float, str]]:
        """
        Retrieves top_k scoring passages across selected documents.
        Returns tuples of (chunk, score, filename).
        """
        all_scored: List[Tuple[DocumentChunk, float, str]] = []

        for did in doc_ids:
            doc = self.get_document(did)
            if not doc:
                continue
            chunks = self.get_chunks(did)
            if not chunks:
                continue
            scored = LexicalRetriever.score_chunks(query, chunks, top_k=top_k)
            for chunk, score in scored:
                all_scored.append((chunk, score, doc.filename))

        all_scored.sort(key=lambda x: x[1], reverse=True)
        return all_scored[:top_k]


document_storage = DocumentStorageService()
