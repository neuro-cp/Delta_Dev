from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_provider_evidence_to_memory_candidate import (
    EvidenceSourceKind,
    ProviderEvidenceCandidateSource,
    convert_provider_evidence_to_candidate,
    validate_evidence_candidate_conversion_safe,
)


REPORT_MD = Path("reports/runtime_v22c_provider_evidence_to_memory_candidate_conversion.md")
REPORT_JSON = Path("reports/runtime_v22c_provider_evidence_to_memory_candidate_conversion.json")


def write_evidence_candidate_conversion_report() -> dict[str, object]:
    cases = [
        convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("provider-demo", EvidenceSourceKind.PROVIDER, "Provider evidence remains evidence until reviewed.", "provider-report")),
        convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("specialist-demo", EvidenceSourceKind.SPECIALIST, "Specialist output is advisory evidence.", "specialist-report")),
        convert_provider_evidence_to_candidate(ProviderEvidenceCandidateSource("evaluator-demo", EvidenceSourceKind.EVALUATOR, "Evaluator output annotates candidates only.", "evaluator-report")),
    ]
    data = {
        "phase": "Runtime V2.2C",
        "cases": cases,
        "all_safe": all(validate_evidence_candidate_conversion_safe(case) for case in cases),
        "final_recommendation": "PROCEED_EVALUATOR_ASSISTED_MEMORY_CANDIDATE_REVIEW",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.2C - Provider Evidence to Memory Candidate Conversion",
        "",
        "Provider, specialist, and evaluator evidence may become candidate proposals only. No canonical memory write is performed.",
        "",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_evidence_candidate_conversion_report()
    print(f"Runtime V2.2C evidence conversion: safe={result['all_safe']} final={result['final_recommendation']}")
