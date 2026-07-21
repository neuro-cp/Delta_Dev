"""Deterministic, offline PDF text extraction for already-authorized bytes."""

from __future__ import annotations

import hashlib
import io
from typing import Any, Callable


def _digest(value: bytes | str) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def extract_governed_pdf_text(
    *,
    pdf_bytes: bytes,
    source_locator: str,
    source_digest: str,
    retrieval_claim_id: str,
    content_type: str = "application/pdf",
    max_bytes: int = 2_000_000,
    max_pages: int = 100,
    max_text_characters: int = 200_000,
    minimum_text_characters: int = 8,
    reader_factory: Callable[[io.BytesIO], Any] | None = None,
) -> dict[str, Any]:
    """Extract bounded page text without network, OCR, or learning interpretation."""

    if not str(content_type).lower().split(";", 1)[0].strip() == "application/pdf":
        return {"status": "rejected", "failure_reason": "pdf_content_type_mismatch"}
    if not source_locator or not retrieval_claim_id:
        return {"status": "rejected", "failure_reason": "pdf_source_or_claim_missing"}
    if len(pdf_bytes) > max_bytes:
        return {"status": "rejected", "failure_reason": "pdf_byte_limit_exceeded"}
    if _digest(pdf_bytes) != str(source_digest):
        return {"status": "rejected", "failure_reason": "pdf_source_digest_mismatch"}
    try:
        if reader_factory is None:
            from pypdf import PdfReader, __version__ as parser_version

            reader_factory = PdfReader
        else:
            parser_version = "injected-test-parser"
        reader = reader_factory(io.BytesIO(pdf_bytes))
        if bool(getattr(reader, "is_encrypted", False)):
            return {"status": "rejected", "failure_reason": "pdf_encrypted_unsupported"}
        pages = tuple(reader.pages)
        if len(pages) > max_pages:
            return {"status": "rejected", "failure_reason": "pdf_page_limit_exceeded"}
        page_records = tuple({"page_number": index + 1, "text": str(page.extract_text() or "").strip()} for index, page in enumerate(pages))
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "failure_reason": f"pdf_parser_exception:{type(exc).__name__}"}
    text = "\n".join(item["text"] for item in page_records).strip()
    if len(text) < minimum_text_characters:
        return {"status": "rejected", "failure_reason": "pdf_extraction_empty_or_implausibly_small"}
    if len(text) > max_text_characters:
        return {"status": "rejected", "failure_reason": "pdf_text_limit_exceeded"}
    return {
        "status": "completed",
        "parser_identity": "pypdf",
        "parser_version": parser_version,
        "source_locator": source_locator,
        "source_digest": source_digest,
        "retrieval_claim_id": retrieval_claim_id,
        "page_count": len(page_records),
        "page_records": page_records,
        "text": text,
        "extraction_warnings": (),
        "extraction_digest": _digest(text),
        "network_access_performed": False,
        "ocr_performed": False,
        "learning_artifact_created": False,
    }
