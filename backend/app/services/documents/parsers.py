"""
NEXORA AI — Document Parsers Framework
Robust parsers for PDF, DOCX, TXT, CSV, XLSX, and Images (with OCR).
Preserves pages, headings, tables, line integrity, and metadata.
"""

import os
import re
import csv
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel
from app.config import settings

# Optional / robust imports
try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from PIL import Image
    import pytesseract
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
except ImportError:
    Image = None
    pytesseract = None


class ParsedPage(BaseModel):
    page_number: int
    content: str
    section: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ParsedDocument(BaseModel):
    filename: str
    file_type: str
    total_pages: int
    pages: List[ParsedPage]
    total_characters: int
    metadata: Dict[str, Any] = {}
    tables: List[Dict[str, Any]] = []


class DocumentParser:
    """Unified document parsing engine with format auto-detection."""

    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".txt", ".csv", ".xlsx",
        ".png", ".jpg", ".jpeg", ".webp"
    }

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def parse_file(cls, file_path: str, original_filename: str) -> ParsedDocument:
        ext = Path(original_filename).suffix.lower()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if ext == ".pdf":
            return cls._parse_pdf(file_path, original_filename)
        elif ext == ".docx":
            return cls._parse_docx(file_path, original_filename)
        elif ext == ".txt":
            return cls._parse_txt(file_path, original_filename)
        elif ext == ".csv":
            return cls._parse_csv(file_path, original_filename)
        elif ext in (".xlsx", ".xls"):
            return cls._parse_xlsx(file_path, original_filename)
        elif ext in (".png", ".jpg", ".jpeg", ".webp"):
            return cls._parse_image(file_path, original_filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @classmethod
    def _parse_pdf(cls, file_path: str, filename: str) -> ParsedDocument:
        if not pypdf:
            raise RuntimeError("pypdf library is required for PDF parsing.")

        pages: List[ParsedPage] = []
        total_chars = 0
        doc_metadata: Dict[str, Any] = {}

        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            if reader.metadata:
                doc_metadata = {
                    "title": reader.metadata.title or "",
                    "author": reader.metadata.author or "",
                    "creator": reader.metadata.creator or ""
                }

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                text = page.extract_text() or ""
                cleaned_text = re.sub(r"[ \t]+", " ", text).strip()

                # If text is virtually empty, try OCR if available
                if len(cleaned_text) < 20 and pytesseract and Image:
                    # Note: Full image extraction from PDF requires pdf2image or PyMuPDF.
                    # As fallback, we record minimal content
                    pass

                pages.append(ParsedPage(
                    page_number=page_num,
                    content=cleaned_text,
                    section=f"Page {page_num}"
                ))
                total_chars += len(cleaned_text)

        except Exception as e:
            raise RuntimeError(f"Failed to parse PDF {filename}: {str(e)}")

        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            total_pages=len(pages),
            pages=pages,
            total_characters=total_chars,
            metadata=doc_metadata
        )

    @classmethod
    def _parse_docx(cls, file_path: str, filename: str) -> ParsedDocument:
        if not docx:
            raise RuntimeError("python-docx library is required for DOCX parsing.")

        pages: List[ParsedPage] = []
        tables_data: List[Dict[str, Any]] = []
        total_chars = 0

        try:
            doc = docx.Document(file_path)
            current_section = "Introduction"
            section_paragraphs: List[str] = []
            page_num = 1

            for p in doc.paragraphs:
                text = p.text.strip()
                if not text:
                    continue
                # Heading detection
                if p.style.name.startswith("Heading"):
                    if section_paragraphs:
                        content_block = "\n".join(section_paragraphs)
                        pages.append(ParsedPage(
                            page_number=page_num,
                            content=content_block,
                            section=current_section
                        ))
                        total_chars += len(content_block)
                        page_num += 1
                        section_paragraphs = []
                    current_section = text
                else:
                    section_paragraphs.append(text)

            if section_paragraphs:
                content_block = "\n".join(section_paragraphs)
                pages.append(ParsedPage(
                    page_number=page_num,
                    content=content_block,
                    section=current_section
                ))
                total_chars += len(content_block)

            # Extract tables
            for t_idx, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_rows.append(row_data)
                if table_rows:
                    tables_data.append({
                        "table_id": t_idx + 1,
                        "rows": table_rows
                    })

            if not pages:
                pages.append(ParsedPage(
                    page_number=1,
                    content="Empty DOCX document.",
                    section="Document"
                ))

        except Exception as e:
            raise RuntimeError(f"Failed to parse DOCX {filename}: {str(e)}")

        return ParsedDocument(
            filename=filename,
            file_type="docx",
            total_pages=len(pages),
            pages=pages,
            total_characters=total_chars,
            tables=tables_data
        )

    @classmethod
    def _parse_txt(cls, file_path: str, filename: str) -> ParsedDocument:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read TXT {filename}: {str(e)}")

        # Split into logical ~3000-character pages for consistency
        chunk_size = 3000
        pages: List[ParsedPage] = []
        total_chars = len(content)

        if not content.strip():
            pages.append(ParsedPage(page_number=1, content="", section="Page 1"))
        else:
            parts = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
            for idx, part in enumerate(parts):
                pages.append(ParsedPage(
                    page_number=idx + 1,
                    content=part.strip(),
                    section=f"Section {idx + 1}"
                ))

        return ParsedDocument(
            filename=filename,
            file_type="txt",
            total_pages=len(pages),
            pages=pages,
            total_characters=total_chars
        )

    @classmethod
    def _parse_csv(cls, file_path: str, filename: str) -> ParsedDocument:
        rows: List[List[str]] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for r in reader:
                    rows.append(r)
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV {filename}: {str(e)}")

        header = rows[0] if rows else []
        row_count = max(0, len(rows) - 1)
        col_count = len(header)

        # Build readable markdown representation of table
        table_lines = []
        if header:
            table_lines.append("| " + " | ".join(header) + " |")
            table_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
            for r in rows[1:101]: # preview up to first 100 rows
                padded = r + [""] * (len(header) - len(r))
                table_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

        formatted_content = (
            f"CSV Dataset Overview:\n"
            f"- Total Rows: {row_count}\n"
            f"- Total Columns: {col_count}\n"
            f"- Columns: {', '.join(header)}\n\n"
            f"Data Preview (First {min(100, row_count)} rows):\n"
            + "\n".join(table_lines)
        )

        page = ParsedPage(
            page_number=1,
            content=formatted_content,
            section="Dataset Table",
            metadata={"rows": row_count, "columns": col_count, "headers": header}
        )

        return ParsedDocument(
            filename=filename,
            file_type="csv",
            total_pages=1,
            pages=[page],
            total_characters=len(formatted_content),
            tables=[{"headers": header, "rows": rows[1:50]}],
            metadata={"rows": row_count, "columns": col_count}
        )

    @classmethod
    def _parse_xlsx(cls, file_path: str, filename: str) -> ParsedDocument:
        if not openpyxl:
            raise RuntimeError("openpyxl library is required for XLSX parsing.")

        pages: List[ParsedPage] = []
        total_chars = 0
        tables_data: List[Dict[str, Any]] = []

        try:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            for idx, sheet_name in enumerate(wb.sheetnames):
                sheet = wb[sheet_name]
                rows = list(sheet.iter_rows(values_only=True))
                if not rows:
                    continue

                header = [str(c or "") for c in rows[0]]
                content_lines = [
                    f"Sheet: {sheet_name}",
                    f"Rows: {len(rows)} | Columns: {len(header)}",
                    f"Columns: {', '.join(header)}",
                    "",
                    "Data Table:"
                ]
                content_lines.append("| " + " | ".join(header) + " |")
                content_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

                for r in rows[1:101]:
                    str_row = [str(c) if c is not None else "" for c in r]
                    padded = str_row + [""] * (len(header) - len(str_row))
                    content_lines.append("| " + " | ".join(padded[:len(header)]) + " |")

                sheet_content = "\n".join(content_lines)
                pages.append(ParsedPage(
                    page_number=idx + 1,
                    content=sheet_content,
                    section=f"Sheet: {sheet_name}"
                ))
                total_chars += len(sheet_content)
                tables_data.append({
                    "sheet": sheet_name,
                    "headers": header,
                    "rows": [[str(c or "") for c in r] for r in rows[1:30]]
                })

            if not pages:
                pages.append(ParsedPage(page_number=1, content="Empty Excel Workbook", section="Sheet 1"))

        except Exception as e:
            raise RuntimeError(f"Failed to read XLSX {filename}: {str(e)}")

        return ParsedDocument(
            filename=filename,
            file_type="xlsx",
            total_pages=len(pages),
            pages=pages,
            total_characters=total_chars,
            tables=tables_data
        )

    @classmethod
    def _parse_image(cls, file_path: str, filename: str) -> ParsedDocument:
        content = ""
        ocr_engine_available = False

        if Image and pytesseract:
            try:
                img = Image.open(file_path)
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    content = f"[OCR Extracted Text from Image '{filename}']:\n\n{ocr_text.strip()}"
                    ocr_engine_available = True
                else:
                    content = f"[Image '{filename}' processed, but no clear text was detected via OCR.]"
            except Exception as e:
                content = f"[Image '{filename}' uploaded. OCR processing note: {str(e)}]"
        else:
            content = (
                f"[Image '{filename}' uploaded successfully. OCR library pytesseract is not configured or Tesseract is not installed on system PATH.]"
            )

        page = ParsedPage(
            page_number=1,
            content=content,
            section="Image OCR",
            metadata={"ocr_engine_available": ocr_engine_available}
        )

        return ParsedDocument(
            filename=filename,
            file_type="image",
            total_pages=1,
            pages=[page],
            total_characters=len(content),
            metadata={"ocr_engine": "tesseract" if ocr_engine_available else "none"}
        )
