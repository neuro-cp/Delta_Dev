from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v22_provider_evidence_to_memory_candidate import EvidenceSourceKind, ProviderEvidenceCandidateSource, convert_provider_evidence_to_candidate
from orchestration.runtime.v22_provider_evidence_to_memory_candidate_report import write_evidence_candidate_conversion_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert DELTA evidence packets to memory candidate proposals.")
    parser.add_argument("--source-kind", choices=[item.value for item in EvidenceSourceKind], default="provider")
    parser.add_argument("--text", default="Provider evidence remains evidence until reviewed.")
    parser.add_argument("--provenance", default="manual_cli")
    parser.add_argument("--output-report", action="store_true")
    args = parser.parse_args()
    if args.output_report:
        print(json.dumps(write_evidence_candidate_conversion_report(), indent=2))
        return 0
    source = ProviderEvidenceCandidateSource("cli-evidence", EvidenceSourceKind(args.source_kind), args.text, args.provenance)
    print(json.dumps(convert_provider_evidence_to_candidate(source), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
