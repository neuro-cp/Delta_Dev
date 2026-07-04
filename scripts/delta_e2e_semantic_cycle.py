"""Run DELTA's deterministic E2E semantic consolidation cycle harness."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.e2e_semantic_consolidation_cycle import write_reports


def main() -> None:
    payload = write_reports()
    audit = payload["audit"]
    answer = payload["grounded_answer"]
    print(f"cycle_id={audit['cycle_id']}")
    print(f"experience_records={audit['experience_count']}")
    print(f"semantic_records={audit['semantic_count']}")
    print(f"replay_batch_id={audit['replay_batch_id']}")
    print(f"consolidation_candidate_ids={','.join(audit['consolidation_candidate_ids'])}")
    print(f"simulated_consolidated_record_ids={','.join(audit['consolidated_record_ids'])}")
    print(f"inquiry={payload['inquiry']['question']}")
    print(f"retrieved_evidence_ids={','.join(audit['retrieved_evidence_ids'])}")
    print(f"grounded_answer={answer['answer']}")
    print(f"uncertainty_list={' | '.join(answer['uncertainty'])}")
    print(f"safety_flags={audit['safety_flags']}")
    print(f"final_recommendation={audit['final_recommendation']}")


if __name__ == "__main__":
    main()
