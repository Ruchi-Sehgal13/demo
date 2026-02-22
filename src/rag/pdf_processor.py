"""
PDF processing for the IPC–BNS conversion guide: load PDF pages, chunk text with structure awareness
(section headings, table boundaries), and write chunks to JSON for the vector store builder.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import fitz  # PyMuPDF

from src.config import paths

# Match paragraph that starts with optional "Section " then digits (e.g. Section 302).
SECTION_RE = re.compile(r"^\s*(Section\s+)?(\d+[A-Z]?)\b")
TABLE_HEADING_RE = re.compile(r"^Table\s+\d+", re.IGNORECASE)


def load_pdf_pages(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Open the PDF and return a list of dicts, one per page: {"page": 1-based index, "text": page text}.
    Uses PyMuPDF (fitz). Raises FileNotFoundError if the path does not exist.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")
    doc = fitz.open(pdf_path)
    pages: List[Dict[str, Any]] = []
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            pages.append({"page": i + 1, "text": page.get_text("text")})
    finally:
        doc.close()
    return pages


def structure_aware_chunk(
    pages: List[Dict[str, Any]], max_chars: int = 1200
) -> List[Dict[str, Any]]:
    """
    Turn a list of page dicts (page, text) into chunks with metadata. Splits on double newlines;
    starts a new chunk at section headings (Section N) and at "Table N" lines so conversion tables
    stay in separate chunks. Each chunk is {"text": ..., "metadata": {"page": int, "section": str|None}}.
    Merges paragraphs into the same chunk until max_chars would be exceeded.
    """
    chunks: List[Dict[str, Any]] = []

    for page in pages:
        text = page["text"]
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        current = ""
        current_meta = {"page": page["page"], "section": None}

        for para in paras:
            m = SECTION_RE.match(para)
            table_heading = TABLE_HEADING_RE.match(para)
            if m:
                if current:
                    chunks.append({"text": current.strip(), "metadata": current_meta})
                sec = m.group(2)
                current = para + "\n"
                current_meta = {"page": page["page"], "section": sec}
            elif table_heading:
                # Start new chunk at each "Table N: ..." so conversion tables are isolated
                if current:
                    chunks.append({"text": current.strip(), "metadata": current_meta})
                current = para + "\n"
                current_meta = {"page": page["page"], "section": None}
            else:
                if len(current) + len(para) + 2 <= max_chars:
                    current += para + "\n"
                else:
                    chunks.append({"text": current.strip(), "metadata": current_meta})
                    current = para + "\n"

        if current:
            chunks.append({"text": current.strip(), "metadata": current_meta})

    return chunks


def main():
    """
    Load the raw IPC–BNS PDF, chunk it with structure_aware_chunk(), and write the result to
    paths.PROCESSED_CHUNKS (JSON with source, num_chunks, chunks). Run this before building
    the vector store (e.g. scripts/build_vector_store.py).
    """
    pdf_path = Path(paths.RAW_PDF)
    out_path = Path(paths.PROCESSED_CHUNKS)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pages = load_pdf_pages(pdf_path)
    chunks = structure_aware_chunk(pages)

    data = {
        "source": pdf_path.name,
        "num_chunks": len(chunks),
        "chunks": chunks,
    }

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[pdf_processor] Wrote {len(chunks)} chunks to {out_path}")


if __name__ == "__main__":
    main()
