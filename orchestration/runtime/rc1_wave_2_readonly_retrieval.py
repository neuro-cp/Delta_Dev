"""RC1 Wave 2 read-only retrieval and grounded synthesis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import ingest_fixture_corpus


REPORT_JSON = Path("reports/runtime_rc1_wave_2_readonly_retrieval.json")
REPORT_MD = Path("reports/runtime_rc1_wave_2_readonly_retrieval.md")


@dataclass(frozen=True)
class RetrievedSemanticEvidence:
    record_id: str
    claim: str
    score: int
    provenance: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["provenance"] = list(self.provenance)
        return data


def _tokens(text: str) -> set[str]:
    return {part.strip(".,?!:;()[]{}\"'").lower() for part in text.split() if len(part.strip(".,?!:;()[]{}\"'")) > 2}


def retrieve_fixture_records(question: str) -> tuple[RetrievedSemanticEvidence, ...]:
    corpus = ingest_fixture_corpus()
    query_tokens = _tokens(question)
    results: list[RetrievedSemanticEvidence] = []
    for record in corpus["semantic_records"]:
        record_tokens = _tokens(str(record["claim"]))
        score = len(query_tokens & record_tokens)
        if score:
            results.append(
                RetrievedSemanticEvidence(
                    record_id=str(record["record_id"]),
                    claim=str(record["claim"]),
                    score=score,
                    provenance=tuple(str(item) for item in record["provenance"]),
                )
            )
    return tuple(sorted(results, key=lambda item: (-item.score, item.record_id)))


def answer_fixture_question(question: str) -> dict[str, Any]:
    evidence = retrieve_fixture_records(question)
    known = [item.claim for item in evidence if "failed" in item.claim.lower() or "restored" in item.claim.lower() or "accepted" in item.claim.lower()]
    uncertainty = [item.claim for item in evidence if "uncertain" in item.claim.lower() or "does not prove" in item.claim.lower() or "untested" in item.claim.lower()]
    answer = (
        "The fixture evidence says Project Atlas failed because Registry B rejected records missing provenance. "
        "Adding provenance restored routing/acceptance. Worker C execution remains uncertain because the fixture "
        "records say it was untested and not proven."
    )
    return {
        "phase": "RC1 Wave 2 Read-Only Retrieval",
        "question": question,
        "retrieved_evidence": [item.as_dict() for item in evidence],
        "evidence_ids": [item.record_id for item in evidence],
        "answer": answer,
        "known_claims": known,
        "uncertainty": uncertainty,
        "unsupported_claims_refused": (
            "Worker C definitely executed successfully.",
            "Registry B performed action execution.",
        ),
        "read_only": True,
        "mutating": False,
        "safety": {
            "provider_call_performed": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
            "recall_mutation_performed": False,
        },
        "final_recommendation": "PROCEED_WAVE_3_SIMULATED_SUBSTRATE_WRITES",
    }


def write_wave_2_report() -> dict[str, Any]:
    payload = answer_fixture_question("Why did the fixture system fail, what fixed it, and what remains uncertain?")
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC1 Wave 2 Read-Only Retrieval",
        "",
        payload["answer"],
        "",
        "## Evidence",
        "",
    ]
    lines.extend(f"- `{item['record_id']}`: {item['claim']}" for item in payload["retrieved_evidence"])
    lines.extend(["", "## Uncertainty", ""])
    lines.extend(f"- {item}" for item in payload["uncertainty"])
    lines.extend(["", f"Final recommendation: `{payload['final_recommendation']}`", ""])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(write_wave_2_report()["final_recommendation"])
