from __future__ import annotations

import hashlib

from orchestration.runtime.governed_pdf_extraction import extract_governed_pdf_text


def _pdf(texts: tuple[str, ...]) -> bytes:
    objects: dict[int, bytes] = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"}
    page_ids = tuple(4 + index * 2 for index in range(len(texts)))
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>".encode()
    for index, text in enumerate(texts):
        page_id, content_id = page_ids[index], page_ids[index] + 1
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        objects[page_id] = f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> /MediaBox [0 0 612 792] /Contents {content_id} 0 R >>".encode()
        objects[content_id] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id in range(1, max(objects) + 1):
        offsets.append(len(body))
        body.extend(f"{object_id} 0 obj\n".encode() + objects[object_id] + b"\nendobj\n")
    xref = len(body)
    body.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    body.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    body.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(body)


def _extract(pdf: bytes, **kwargs):
    return extract_governed_pdf_text(
        pdf_bytes=pdf,
        source_locator="https://example.test/document.pdf",
        source_digest=hashlib.sha256(pdf).hexdigest(),
        retrieval_claim_id="claim-fixture",
        **kwargs,
    )


def test_extracts_text_and_has_deterministic_digest_for_multiple_pages():
    pdf = _pdf(("Unrelated climate observation.", "Second unrelated page."))
    first = _extract(pdf)
    second = _extract(pdf)
    assert first["status"] == "completed"
    assert first["page_count"] == 2
    assert first["extraction_digest"] == second["extraction_digest"]
    assert first["network_access_performed"] is False
    assert first["learning_artifact_created"] is False
    assert "spectral" not in first["text"].lower()


def test_rejects_digest_content_page_byte_and_empty_text_failures():
    pdf = _pdf(("Useful fixture text.",))
    assert extract_governed_pdf_text(pdf_bytes=pdf, source_locator="https://example.test/a.pdf", source_digest="wrong", retrieval_claim_id="claim")["failure_reason"] == "pdf_source_digest_mismatch"
    assert _extract(pdf, content_type="text/html")["failure_reason"] == "pdf_content_type_mismatch"
    assert _extract(pdf, max_bytes=10)["failure_reason"] == "pdf_byte_limit_exceeded"
    assert _extract(pdf, max_pages=0)["failure_reason"] == "pdf_page_limit_exceeded"
    assert _extract(_pdf(("",)))["failure_reason"] == "pdf_extraction_empty_or_implausibly_small"


def test_rejects_malformed_and_parser_exception_without_ocr_or_network():
    malformed = b"not-a-pdf"
    assert _extract(malformed)["status"] == "failed"
    pdf = _pdf(("Useful fixture text.",))
    failed = _extract(pdf, reader_factory=lambda _: (_ for _ in ()).throw(RuntimeError("fixture")))
    assert failed == {"status": "failed", "failure_reason": "pdf_parser_exception:RuntimeError"}
