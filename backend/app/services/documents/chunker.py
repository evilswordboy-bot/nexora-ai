"""
NEXORA AI — Semantic Text Chunker & Passage Indexer
Splits documents into overlapping chunks with preserved boundary lines,
headings, page numbers, and fast lexical TF-IDF / BM25-style keyword matching.
"""

import math
import re
from typing import List, Dict, Any, Tuple
from app.models.schemas import DocumentChunk


class DocumentChunker:
    """Intelligent recursive text chunker that preserves paragraphs and sentences."""

    def __init__(self, target_chunk_tokens: int = 500, overlap_tokens: int = 50):
        self.target_chunk_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens
        # Rough heuristic: 1 token ~= 4 characters in English
        self.target_chars = target_chunk_tokens * 4
        self.overlap_chars = overlap_tokens * 4

    def chunk_document(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Takes parsed pages and produces indexed, page-referenced chunks."""
        chunks: List[DocumentChunk] = []
        global_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            section = page.get("section") or f"Page {page_num}"
            content = page.get("content", "").strip()

            if not content:
                continue

            # If page text is within limit, make single chunk
            if len(content) <= self.target_chars:
                token_count = max(1, len(content.split()))
                chunks.append(DocumentChunk(
                    id=f"{document_id}_c{global_idx}",
                    document_id=document_id,
                    chunk_index=global_idx,
                    page_number=page_num,
                    section=section,
                    content=content,
                    token_count=token_count
                ))
                global_idx += 1
                continue

            # Split by double newlines (paragraphs)
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            current_buffer: List[str] = []
            current_len = 0

            for para in paragraphs:
                if current_len + len(para) > self.target_chars and current_buffer:
                    chunk_text = "\n\n".join(current_buffer)
                    chunks.append(DocumentChunk(
                        id=f"{document_id}_c{global_idx}",
                        document_id=document_id,
                        chunk_index=global_idx,
                        page_number=page_num,
                        section=section,
                        content=chunk_text,
                        token_count=max(1, len(chunk_text.split()))
                    ))
                    global_idx += 1
                    # Retain last paragraph for overlap
                    current_buffer = [current_buffer[-1], para] if len(current_buffer) > 1 else [para]
                    current_len = sum(len(p) for p in current_buffer)
                else:
                    current_buffer.append(para)
                    current_len += len(para)

            if current_buffer:
                chunk_text = "\n\n".join(current_buffer)
                chunks.append(DocumentChunk(
                    id=f"{document_id}_c{global_idx}",
                    document_id=document_id,
                    chunk_index=global_idx,
                    page_number=page_num,
                    section=section,
                    content=chunk_text,
                    token_count=max(1, len(chunk_text.split()))
                ))
                global_idx += 1

        return chunks


class LexicalRetriever:
    """
    High-speed BM25 / TF-IDF style lexical retriever for passage retrieval
    without requiring external heavyweight vector databases or network calls.
    """

    @classmethod
    def score_chunks(
        cls,
        query: str,
        chunks: List[DocumentChunk],
        top_k: int = 5
    ) -> List[Tuple[DocumentChunk, float]]:
        if not chunks:
            return []

        # Tokenize query
        stop_words = {
            "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
            "is", "are", "was", "were", "what", "which", "how", "why", "when",
            "where", "who", "whom", "this", "that", "it", "with", "as", "by"
        }
        query_terms = [
            t for t in re.findall(r"\b\w{3,}\b", query.lower())
            if t not in stop_words
        ]

        if not query_terms:
            # Fallback to general words if all words were small/stopwords
            query_terms = re.findall(r"\b\w+\b", query.lower())

        if not query_terms:
            return [(c, 1.0) for c in chunks[:top_k]]

        # Compute document frequency (DF)
        df: Dict[str, int] = {}
        total_docs = len(chunks)
        tokenized_chunks = []

        for c in chunks:
            words = set(re.findall(r"\b\w+\b", c.content.lower()))
            tokenized_chunks.append(words)
            for w in words:
                df[w] = df.get(w, 0) + 1

        scores: List[Tuple[DocumentChunk, float]] = []

        for idx, chunk in enumerate(chunks):
            words_in_chunk = tokenized_chunks[idx]
            raw_text = chunk.content.lower()
            score = 0.0

            for q in query_terms:
                if q in words_in_chunk:
                    # IDF component
                    idf = math.log((total_docs - df.get(q, 0) + 0.5) / (df.get(q, 0) + 0.5) + 1.0)
                    # Frequency bonus
                    count = raw_text.count(q)
                    score += idf * (1.0 + math.log(count))

            # Phrase match bonus if full sub-phrases appear
            if len(query.strip()) > 5 and query.lower() in raw_text:
                score += 5.0

            if score > 0:
                scores.append((chunk, score))

        # Sort descending by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # If zero matches found (e.g. diverse terminology), return top initial chunks
        if not scores:
            return [(c, 0.1) for c in chunks[:top_k]]

        return scores[:top_k]
