import re
from typing import Dict


def _normalize_evidence_text(text: str) -> str:
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text.strip()


def isolate_quote_instruction_boundary(text: str) -> Dict:
    """
    Isolate the first quoted span from the text, mark it as non-authoritative,
    extract dependency ids (like DEP-404) from the remaining text,
    and return structured information.

    Returns dict with keys:
      - quoted_text: str or None
      - quoted_text_authoritative: bool (always False)
      - dependency_id: str or None
      - evidence_text: str (remaining text after removing quoted span)
      - instruction_executed: bool (always False)
    """
    quote_pattern = re.compile(r"""(['"])(.+?)\1""")
    match = quote_pattern.search(text)

    quoted_text = None
    quoted_text_authoritative = False
    evidence_text = text

    if match:
        quoted_text = match.group(2)
        start, end = match.span()
        evidence_text = text[:start] + text[end:]
        evidence_text = _normalize_evidence_text(evidence_text)

    dep_pattern = re.compile(r"\bDEP-\d+\b")
    dep_match = dep_pattern.search(evidence_text)
    dependency_id = dep_match.group(0) if dep_match else None

    return {
        "quoted_text": quoted_text,
        "quoted_text_authoritative": quoted_text_authoritative,
        "dependency_id": dependency_id,
        "evidence_text": evidence_text,
        "instruction_executed": False,
    }
