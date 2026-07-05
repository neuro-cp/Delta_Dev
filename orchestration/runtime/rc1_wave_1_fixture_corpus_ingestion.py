"""RC1 Wave 1 fixture-only corpus ingestion.

Fixture ingestion writes only noncanonical semantic records to an explicit
workspace. It performs no provider calls, training, memory mutation, canonical
writes, schedulers, or live arbitrary ingestion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_JSON = Path("reports/runtime_rc1_wave_1_fixture_corpus_ingestion.json")
REPORT_MD = Path("reports/runtime_rc1_wave_1_fixture_corpus_ingestion.md")
FIXTURE_DIR = Path("data/rc1_fixture_corpus")


@dataclass(frozen=True)
class FixtureDocument:
    document_id: str
    path: str
    checksum: str
    text: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NoncanonicalSemanticRecord:
    record_id: str
    source_document_id: str
    source_path: str
    source_checksum: str
    claim: str
    provenance: tuple[str, ...]
    noncanonical: bool = True
    canonical_write_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]


def load_fixture_documents(input_dir: str | Path = FIXTURE_DIR) -> tuple[FixtureDocument, ...]:
    root = Path(input_dir)
    allowed = {".txt", ".md"}
    documents: list[FixtureDocument] = []
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in allowed or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        documents.append(
            FixtureDocument(
                document_id=f"fixture-doc-{_digest(path.name, checksum)}",
                path=str(path.as_posix()),
                checksum=checksum,
                text=text,
            )
        )
    return tuple(documents)


def build_semantic_records(documents: tuple[FixtureDocument, ...]) -> tuple[NoncanonicalSemanticRecord, ...]:
    records: list[NoncanonicalSemanticRecord] = []
    for document in documents:
        sentences = [part.strip(" \n#") for part in document.text.replace("\n", " ").split(".") if part.strip(" \n#")]
        for sentence in sentences:
            records.append(
                NoncanonicalSemanticRecord(
                    record_id=f"noncanonical-semantic-{_digest(document.document_id, sentence)}",
                    source_document_id=document.document_id,
                    source_path=document.path,
                    source_checksum=document.checksum,
                    claim=sentence + ".",
                    provenance=(document.document_id, document.path),
                )
            )
    return tuple(records)


def ingest_fixture_corpus(
    input_dir: str | Path = FIXTURE_DIR,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    documents = load_fixture_documents(input_dir)
    records = build_semantic_records(documents)
    output_path = Path(output_dir) if output_dir else None
    if output_path is not None:
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "semantic_records.json").write_text(
            json.dumps([record.as_dict() for record in records], indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return {
        "phase": "RC1 Wave 1 Fixture Corpus Ingestion",
        "input_dir": str(Path(input_dir).as_posix()),
        "output_dir": str(output_path.as_posix()) if output_path else None,
        "fixture_only": True,
        "documents": [document.as_dict() for document in documents],
        "semantic_records": [record.as_dict() for record in records],
        "record_count": len(records),
        "rollback_plan": "Delete the noncanonical Wave 1 output folder for this run.",
        "safety": {
            "provider_call_performed": False,
            "training_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "canonical_write_performed": False,
            "scheduler_started": False,
            "hyb1": "dormant_env_gated",
            "model_b_default": "unchanged",
        },
        "final_recommendation": "PROCEED_WAVE_2_READ_ONLY_RETRIEVAL",
    }


def write_wave_1_report() -> dict[str, Any]:
    payload = ingest_fixture_corpus()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC1 Wave 1 Fixture Corpus Ingestion",
        "",
        f"- fixture_only: {payload['fixture_only']}",
        f"- documents: {len(payload['documents'])}",
        f"- semantic_records: {payload['record_count']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Records",
        "",
    ]
    lines.extend(f"- `{record['record_id']}`: {record['claim']}" for record in payload["semantic_records"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    report = write_wave_1_report()
    print(report["final_recommendation"])
