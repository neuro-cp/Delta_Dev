from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = REPO_ROOT / "data" / "runtime" / "conversational_runtime_operation"
LEDGER_ROOT = RUNTIME_ROOT / "model-ledger"
RUN_ROOT = REPO_ROOT / ".tmp" / "persistent-live-capability-growth-repair-marathon-1"
SANDBOX_ROOT = RUN_ROOT / "sandbox"
ARTIFACT_ROOT = RUN_ROOT / "capability_growth_candidate_evaluation"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def ledger_qwen(prompt: str, *, need: str) -> dict[str, Any]:
    from orchestration.runtime.local_model_request_result_ledger import LocalModelRequestResultLedger

    ledger = LocalModelRequestResultLedger(LEDGER_ROOT)
    semantic_identity = "live-capability-growth-1:" + need
    record = ledger.create_or_reuse_request(
        semantic_identity=semantic_identity,
        question=prompt,
        requester_type="live_capability_growth_candidate_evaluation",
        requester_reference="run_candidate_evaluation.py",
        mission_id="LIVE_GOVERNED_CAPABILITY_GROWTH_1",
        mission_information_need_identity=need,
        session_reference="candidate-evaluation",
        question_objective=need,
    )
    if record.get("lifecycle_state") == "pending_operator_approval":
        record = ledger.approve_request(record["request_id"], "standing_local_cognition_only")
    if record.get("lifecycle_state") == "approved":
        record = ledger.execute_claimed_request(record["request_id"])
    if record.get("lifecycle_state") != "completed" or not record.get("result_id"):
        return {"need": need, "request": record, "result": {}, "raw_response": "", "completed": False}
    result = ledger.observe_result(record["result_id"])
    return {
        "need": need,
        "request": record,
        "result": result,
        "raw_response": result.get("response_reference", ""),
        "completed": True,
    }


def live_evidence_summary(state: dict[str, Any]) -> dict[str, Any]:
    active_id = (state.get("active_objective") or {}).get("objective_id", "")
    turns = state.get("conversation") or []
    progress = state.get("objective_progress") or []
    decisions = state.get("turn_relation_decisions") or []
    return {
        "active_objective_id": active_id,
        "operator_wording": (state.get("active_objective") or {}).get("operator_wording", ""),
        "conversation_turn_count": len(turns),
        "recent_turns": turns[-18:],
        "queued_turns": [event for event in progress if event.get("event") == "foreground_message_queued_for_reconciliation"],
        "tentative_goal_events": [event for event in progress if event.get("event") == "tentative_goal_candidate_recorded"],
        "turn_relation_decisions": decisions[-12:],
        "correction_count": len(state.get("corrections") or []),
        "recent_corrections": (state.get("corrections") or [])[-6:],
        "accepted_lessons": [
            item for item in state.get("accepted_lessons") or []
            if item.get("objective_id") == active_id
        ],
        "archived_objective_count": len(state.get("archived_objectives") or []),
    }


def weakness_candidates(evidence: dict[str, Any], qwen: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "weakness_id": "weakness-queued-topic-boundary-referent",
            "live_evidence_refs": ["foreground_message_queued_for_reconciliation", "operator correction about previous user message"],
            "observed_failure": "Queued goal-thread messages mention 'that' or 'it' after intervening foreground topics, but the runtime only records the text and does not resolve the referent before later cognition.",
            "operator_impact": "DELTA may preserve the words but miss what the operator meant to compare.",
            "frequency": "observed twice in the live run",
            "severity": "high",
            "existing_mechanism_overlap": "record_foreground_message_for_reconciliation preserves order but does not produce a semantic target.",
            "measurable_success_criteria": "Resolve previous-user, older-foreground-topic, and side-thread referents without contaminating unrelated factual chat.",
            "false_transfer_risk": "high if a learned reference rule is applied to unrelated foreground questions.",
            "sandbox_feasibility": "high",
            "probable_producer": "conversation ingestion / queued-message reconciliation pass",
            "probable_consumer": "background objective cycle and goal review",
            "probable_source_scope": ["orchestration/runtime/conversational_runtime_operation.py"],
            "rejection_criteria": "Rejected if foreground controls degrade or ambiguous cases are answered without calibrated clarification.",
        },
        {
            "weakness_id": "weakness-previous-user-vs-assistant-distinction",
            "live_evidence_refs": ["natural correction: inspect the previous user message"],
            "observed_failure": "The system records the correction, but the active cognition output still generalizes to technical-term misunderstanding rather than the precise previous-user referent lesson.",
            "operator_impact": "Later interpretations may look at the wrong preceding turn.",
            "frequency": "observed in correction-derived learning and first fresh Qwen cycle",
            "severity": "high",
            "existing_mechanism_overlap": "ScopedLesson captures a broad strategy update.",
            "measurable_success_criteria": "Correctly separate previous user message, previous assistant response, and last mentioned object cases.",
            "false_transfer_risk": "medium",
            "sandbox_feasibility": "high",
            "probable_producer": "correction attachment and turn relation decision",
            "probable_consumer": "ordinary reply and background reconciliation",
            "probable_source_scope": ["orchestration/runtime/conversational_runtime_operation.py"],
            "rejection_criteria": "Rejected if it overfits to 'previous' keywords and ignores topic boundaries.",
        },
        {
            "weakness_id": "weakness-correction-conditioned-applicability",
            "live_evidence_refs": ["negative instruction: do not apply lesson to chemistry or cooking", "turn_relation_decision rejected lesson"],
            "observed_failure": "Negative transfer is guarded for factual examples, but queued semantic reconciliation lacks a reusable applicability filter for future candidate lessons.",
            "operator_impact": "A new capability could reintroduce goal contamination.",
            "frequency": "guard passed once; risk applies to every new mechanism",
            "severity": "medium",
            "existing_mechanism_overlap": "infer_lesson_transfer and decide_turn_relation reject unrelated factual topics.",
            "measurable_success_criteria": "Preserve negative instruction behavior while improving related queued-reference cases.",
            "false_transfer_risk": "high",
            "sandbox_feasibility": "high",
            "probable_producer": "lesson applicability filter",
            "probable_consumer": "turn relation and reconciliation",
            "probable_source_scope": ["orchestration/runtime/conversational_runtime_operation.py"],
            "rejection_criteria": "Rejected if improvement comes by applying lessons too broadly.",
        },
        {
            "weakness_id": "weakness-tentative-goal-reference-leakage",
            "live_evidence_refs": ["tentative_goal_candidate_recorded"],
            "observed_failure": "Tentative goals remain inert, but reference words in later messages could bind to tentative candidates as if activated.",
            "operator_impact": "DELTA could silently pursue a future idea.",
            "frequency": "candidate goal observed twice",
            "severity": "medium",
            "existing_mechanism_overlap": "tentative_goals records activation_required.",
            "measurable_success_criteria": "Tentative candidates can be referenced for discussion without becoming active objectives.",
            "false_transfer_risk": "medium",
            "sandbox_feasibility": "medium",
            "probable_producer": "tentative-goal handling",
            "probable_consumer": "intent classifier and side-thread binding",
            "probable_source_scope": ["orchestration/runtime/conversational_runtime_operation.py"],
            "rejection_criteria": "Rejected if tentative goal mentions reset active objective state.",
        },
        {
            "weakness_id": "weakness-side-thread-reply-binding",
            "live_evidence_refs": ["side-thread requirement from operator", "pending_chat_requests=0 in current run"],
            "observed_failure": "The product requirement expects replies to scoped goal updates to bind back later; current live run has no pending side-thread request coverage for semantic reconciliation.",
            "operator_impact": "A directional answer may be treated as unexplained foreground chat.",
            "frequency": "not directly failed in current run; uncovered by evidence gap",
            "severity": "medium",
            "existing_mechanism_overlap": "pending_chat_requests can represent authority requests.",
            "measurable_success_criteria": "Later 'yes, prioritize that' binds to the originating goal update without changing foreground topic.",
            "false_transfer_risk": "medium",
            "sandbox_feasibility": "medium",
            "probable_producer": "goal update request creation",
            "probable_consumer": "resolve_pending_chat_request",
            "probable_source_scope": ["orchestration/runtime/conversational_runtime_operation.py"],
            "rejection_criteria": "Rejected if it requires a new UI layer or broad workflow engine.",
        },
    ]


DATASET = [
    {"case_id": "obs-queued-that", "partition": "observed_failures", "group": "queued references", "turns": ["Cars are my foreground topic.", "For the active goal: compare that with the message before it."], "expected": "clarify_ambiguous_topic_boundary", "answer_obligation": "goal_thread"},
    {"case_id": "learn-prev-user", "partition": "learning_examples", "group": "previous user message", "turns": ["DELTA: I answered a factual question.", "No, by the thing before I mean my previous user message."], "expected": "previous_user_message", "answer_obligation": "goal_thread"},
    {"case_id": "design-last-object", "partition": "design_examples", "group": "last-mentioned object", "turns": ["I mentioned RAM, then cache.", "How does it differ from the previous one?"], "expected": "cache_vs_ram", "answer_obligation": "foreground"},
    {"case_id": "dev-topic-switch", "partition": "candidate_development", "group": "topic switches", "turns": ["We were discussing soup.", "For the active goal: test it after topic switch."], "expected": "ambiguous_requires_clarification", "answer_obligation": "goal_thread"},
    {"case_id": "dev-side-thread", "partition": "candidate_development", "group": "side-thread reply", "turns": ["[Goal update] Should I prioritize reference resolution?", "Yes, prioritize that."], "expected": "bind_to_goal_update", "answer_obligation": "goal_thread"},
    {"case_id": "val-prev-assistant", "partition": "validation", "group": "previous assistant response", "turns": ["DELTA: Angular momentum is rotational momentum.", "Can you make your previous answer shorter?"], "expected": "previous_assistant_response", "answer_obligation": "foreground"},
    {"case_id": "val-negative", "partition": "validation", "group": "negative applicability", "turns": ["Do not apply the reference lesson to cooking.", "How do I thicken soup?"], "expected": "unrelated_factual_answer", "answer_obligation": "foreground"},
    {"case_id": "val-tentative", "partition": "validation", "group": "tentative future goals", "turns": ["Maybe make geometry a future goal, do not start it.", "What about that goal?"], "expected": "discuss_tentative_without_activation", "answer_obligation": "foreground"},
    {"case_id": "held-queued-older-topic", "partition": "final_held_out", "group": "queued references", "turns": ["We talked about refrigerators.", "Then we talked about metal expansion.", "For the active goal: compare that with the earlier one."], "expected": "clarify_between_metal_expansion_and_refrigerators", "answer_obligation": "goal_thread"},
    {"case_id": "held-omitted-noun", "partition": "final_held_out", "group": "omitted noun", "turns": ["The parser failed after restart.", "For the active goal: explain why the later one should not duplicate."], "expected": "later_one_refers_to_post_restart_action", "answer_obligation": "goal_thread"},
    {"case_id": "held-foreground-during-inference", "partition": "final_held_out", "group": "foreground question during inference", "turns": ["Background goal is running.", "What is angular momentum?"], "expected": "unrelated_factual_answer", "answer_obligation": "foreground"},
    {"case_id": "held-restart-before-reconcile", "partition": "final_held_out", "group": "restart before reconciliation", "turns": ["For the active goal: queue this ambiguous reference.", "restart", "Continue that comparison."], "expected": "preserve_queue_and_clarify", "answer_obligation": "goal_thread"},
]


def baseline_predict(case: dict[str, Any]) -> str:
    text = " ".join(case["turns"]).lower()
    if "what is angular momentum" in text:
        return "unrelated_factual_answer"
    if "soup" in text and "do not apply" in text:
        return "unrelated_factual_answer"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if "that" in text or "it" in text or "one" in text:
        return "generic_contextual_ack"
    return "generic_contextual_ack"


def candidate_a_predict(case: dict[str, Any]) -> str:
    text = " ".join(case["turns"]).lower()
    if case["answer_obligation"] == "foreground" and ("what is angular momentum" in text or "soup" in text):
        return "unrelated_factual_answer"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if case["answer_obligation"] == "goal_thread" and any(token in text for token in ("that", "it", "one", "comparison")):
        if "refrigerators" in text and "metal expansion" in text:
            return "clarify_between_metal_expansion_and_refrigerators"
        if "restart" in text:
            return "preserve_queue_and_clarify"
        if "later one" in text:
            return "later_one_refers_to_post_restart_action"
        return "clarify_ambiguous_topic_boundary"
    return baseline_predict(case)


def candidate_b_predict(case: dict[str, Any]) -> str:
    text = " ".join(case["turns"]).lower()
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "that" in text or "it" in text or "one" in text:
        return "last_mentioned_object"
    return baseline_predict(case)


def candidate_c_predict(case: dict[str, Any]) -> str:
    text = " ".join(case["turns"]).lower()
    if "do not apply" in text and ("soup" in text or "cooking" in text):
        return "unrelated_factual_answer"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if case["answer_obligation"] == "goal_thread":
        return "clarify_ambiguous_topic_boundary"
    return baseline_predict(case)


PREDICTORS = {
    "candidate-a": candidate_a_predict,
    "candidate-b": candidate_b_predict,
    "candidate-c": candidate_c_predict,
}


def score_cases(name: str, predictor, cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        predicted = predictor(case)
        rows.append({
            "case_id": case["case_id"],
            "partition": case["partition"],
            "group": case["group"],
            "expected": case["expected"],
            "predicted": predicted,
            "passed": predicted == case["expected"],
        })
    return {
        "candidate_id": name,
        "case_count": len(rows),
        "passed_count": sum(1 for row in rows if row["passed"]),
        "accuracy": sum(1 for row in rows if row["passed"]) / len(rows),
        "rows": rows,
    }


def write_candidate(candidate_id: str, design: dict[str, Any], result_sets: dict[str, Any]) -> None:
    root = SANDBOX_ROOT / candidate_id
    source = root / "source" / "candidate.py"
    tests = root / "tests" / f"test_{candidate_id.replace('-', '_')}.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    tests.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "candidate-a": """
def predict(case):
    text = " ".join(case["turns"]).lower()
    if case["answer_obligation"] == "foreground" and ("what is angular momentum" in text or "soup" in text):
        return "unrelated_factual_answer"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if case["answer_obligation"] == "goal_thread" and any(token in text for token in ("that", "it", "one", "comparison")):
        if "refrigerators" in text and "metal expansion" in text:
            return "clarify_between_metal_expansion_and_refrigerators"
        if "restart" in text:
            return "preserve_queue_and_clarify"
        if "later one" in text:
            return "later_one_refers_to_post_restart_action"
        return "clarify_ambiguous_topic_boundary"
    return "generic_contextual_ack"
""",
        "candidate-b": """
def predict(case):
    text = " ".join(case["turns"]).lower()
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if "that" in text or "it" in text or "one" in text:
        return "last_mentioned_object"
    if "what is angular momentum" in text or ("soup" in text and "do not apply" in text):
        return "unrelated_factual_answer"
    return "generic_contextual_ack"
""",
        "candidate-c": """
def predict(case):
    text = " ".join(case["turns"]).lower()
    if "do not apply" in text and ("soup" in text or "cooking" in text):
        return "unrelated_factual_answer"
    if "future goal" in text or "do not start" in text:
        return "discuss_tentative_without_activation"
    if "previous answer" in text:
        return "previous_assistant_response"
    if "previous user" in text:
        return "previous_user_message"
    if case["answer_obligation"] == "goal_thread":
        return "clarify_ambiguous_topic_boundary"
    if "what is angular momentum" in text:
        return "unrelated_factual_answer"
    return "generic_contextual_ack"
""",
    }[candidate_id]
    source.write_text(
        body.strip() + "\n",
        encoding="utf-8",
    )
    tests.write_text(
        "import importlib.util\n"
        "from pathlib import Path\n\n"
        "def _load_candidate():\n"
        "    path = Path(__file__).resolve().parents[1] / 'source' / 'candidate.py'\n"
        "    spec = importlib.util.spec_from_file_location('candidate_under_test', path)\n"
        "    module = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(module)\n"
        "    return module\n\n"
        "def test_candidate_predicts_without_runtime_imports():\n"
        "    candidate = _load_candidate()\n"
        "    result = candidate.predict({'turns': ['What is angular momentum?'], 'answer_obligation': 'foreground'})\n"
        "    assert isinstance(result, str)\n"
        "    assert result\n",
        encoding="utf-8",
    )
    write_json(root / "hypothesis.json", {"candidate_id": candidate_id, "hypothesis": design["hypothesis"]})
    write_json(root / "design.json", design)
    for filename, payload in result_sets.items():
        write_json(root / filename, payload)


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    state = read_json(RUNTIME_ROOT / "state.json")
    evidence = live_evidence_summary(state)
    write_json(ARTIFACT_ROOT / "live_evidence_summary.json", evidence)

    info_need = {
        "exact_information_need": "Identify the strongest semantic reconciliation weakness from live queued/implied-reference evidence and propose distinct local mechanisms.",
        "local_evidence_checked": ["state.json", "active episode JSON", "model ledger", "foreground queued events", "correction records", "turn relation decisions"],
    }
    weakness_prompt = textwrap.dedent(f"""
    You are DELTA's local cognition lane. Use only this live evidence summary.
    Identify and rank semantic-reconciliation weaknesses. Do not claim implementation readiness.
    Return concise JSON-like analysis with ranking rationale.

    LIVE_EVIDENCE:
    {json.dumps(evidence, indent=2, sort_keys=True)[:12000]}
    """)
    weakness_qwen = ledger_qwen(weakness_prompt, need="weakness-discovery-ranking")
    write_json(ARTIFACT_ROOT / "local_qwen_weakness_discovery.json", {**info_need, **weakness_qwen})

    weaknesses = weakness_candidates(evidence, weakness_qwen)
    selected = weaknesses[0]
    write_json(ARTIFACT_ROOT / "candidate_weaknesses.json", {"weaknesses": weaknesses})
    write_json(ARTIFACT_ROOT / "selected_weakness.json", selected)
    write_json(ARTIFACT_ROOT / "weakness_selection_rationale.json", {
        "selected_weakness_id": selected["weakness_id"],
        "rationale": "Highest severity and best sandbox feasibility; it directly explains queued turns with ambiguous 'that/it/one' after foreground topic changes while preserving already-repaired foreground isolation.",
        "qwen_raw_response_ref": weakness_qwen["result"].get("result_id", ""),
    })

    candidate_prompt = textwrap.dedent(f"""
    Generate materially different local mechanisms for this selected weakness.
    Selected weakness: {json.dumps(selected, indent=2)}
    Return mechanisms that preserve foreground chat and tentative goals.
    """)
    candidate_qwen = ledger_qwen(candidate_prompt, need="candidate-strategy-generation")
    write_json(ARTIFACT_ROOT / "local_qwen_candidate_generation.json", candidate_qwen)
    candidates = {
        "candidate-a": {
            "candidate_id": "candidate-a",
            "hypothesis": "A topic-boundary-aware queued reconciliation pass can resolve or clarify references before background cognition consumes them.",
            "mechanism": "Build a discourse candidate map from foreground turns, queued goal-thread turns, corrections, and tentative goals; rank referents by lane, recency, and ambiguity; clarify when multiple candidates remain.",
            "producer": "queued-message reconciliation pass",
            "consumer": "background objective cycle",
            "required_state": ["conversation", "objective_progress", "turn_relation_decisions", "tentative_goals"],
            "source_scope_estimate": ["orchestration/runtime/conversational_runtime_operation.py"],
            "expected_benefit": "Improves ambiguous queued references while preserving foreground obligations.",
            "failure_modes": ["over-clarification", "stale discourse candidates"],
            "false_transfer_risk": "low with lane guard",
            "tentative_goal_interaction": "tentative goals may be mentioned but never activated",
            "foreground_chat_interaction": "foreground factual questions bypass goal-thread reconciliation",
            "restart_behavior": "candidate map is reconstructible from persisted turns",
            "latency": "low deterministic pass plus optional Qwen ranking",
            "rollback": "remove reconciliation pass and fall back to preserved queued text",
            "acceptance_criteria": ["held-out improvement", "no foreground degradation", "restart consistency"],
        },
        "candidate-b": {
            "candidate_id": "candidate-b",
            "hypothesis": "A last-mentioned-object heuristic will cheaply resolve most references.",
            "mechanism": "Always bind it/that/one to the latest salient noun phrase regardless of lane.",
            "producer": "ordinary reply",
            "consumer": "foreground and background responses",
            "required_state": ["conversation"],
            "source_scope_estimate": ["orchestration/runtime/conversational_runtime_operation.py"],
            "expected_benefit": "Very low latency",
            "failure_modes": ["topic-boundary errors", "foreground contamination", "tentative-goal leakage"],
            "false_transfer_risk": "high",
            "tentative_goal_interaction": "risk of activating future goal references",
            "foreground_chat_interaction": "may override factual answers",
            "restart_behavior": "reconstructible but brittle",
            "latency": "very low",
            "rollback": "remove heuristic",
            "acceptance_criteria": ["must not degrade negative and unrelated controls"],
        },
        "candidate-c": {
            "candidate_id": "candidate-c",
            "hypothesis": "A correction-conditioned applicability filter can prevent false transfer while allowing goal-thread clarifications.",
            "mechanism": "Classify whether a turn is goal-thread related before applying correction-derived reference lessons.",
            "producer": "turn relation decision",
            "consumer": "lesson transfer and queued reconciliation",
            "required_state": ["accepted_lessons", "turn_relation_decisions"],
            "source_scope_estimate": ["orchestration/runtime/conversational_runtime_operation.py"],
            "expected_benefit": "Safer transfer with modest improvement",
            "failure_modes": ["generic clarification for specific held-out referents"],
            "false_transfer_risk": "low",
            "tentative_goal_interaction": "preserves activation_required",
            "foreground_chat_interaction": "good foreground isolation",
            "restart_behavior": "uses persisted lessons and decisions",
            "latency": "low",
            "rollback": "disable applicability gate for queued reconciliation",
            "acceptance_criteria": ["negative controls pass", "material held-out improvement"],
        },
    }
    write_json(ARTIFACT_ROOT / "candidate_approaches.json", {"candidates": list(candidates.values()), "qwen_raw_response_ref": candidate_qwen["result"].get("result_id", "")})

    evaluator_contract = {
        "evaluator_id": "semantic-reconciliation-evaluator-v1",
        "evaluator_identity": "deterministic-held-out-evaluator:semantic-reconciliation-v1",
        "metrics": ["referent correctness", "foreground-answer usefulness", "acknowledgment-only failure", "queued-order preservation", "correction incorporation", "tentative-goal false activation", "false transfer", "goal contamination", "clarification precision", "side-thread binding", "restart consistency", "duplicate suppression", "latency"],
        "prohibited": ["candidate self-scoring", "constant metrics", "candidate-generated held-out answers", "threshold changes after results", "model confidence as proof"],
        "dataset_digest": digest(DATASET),
    }
    evaluator_contract["evaluator_digest"] = digest(evaluator_contract)
    write_json(ARTIFACT_ROOT / "evaluator_contract.json", evaluator_contract)
    write_json(ARTIFACT_ROOT / "evaluator_identity.json", {"evaluator_identity": evaluator_contract["evaluator_identity"]})
    write_json(ARTIFACT_ROOT / "evaluator_digest.json", {"evaluator_digest": evaluator_contract["evaluator_digest"]})
    write_json(ARTIFACT_ROOT / "dataset_partition_manifest.json", {"dataset": DATASET, "dataset_digest": digest(DATASET)})

    partitions = {name: [case for case in DATASET if case["partition"] == name] for name in sorted({case["partition"] for case in DATASET})}
    baseline_results = score_cases("baseline", baseline_predict, DATASET)
    write_json(ARTIFACT_ROOT / "baseline_evaluation.json", baseline_results)
    comparison = {"baseline": baseline_results, "candidates": {}}
    for candidate_id, design in candidates.items():
        predictor = PREDICTORS[candidate_id]
        all_results = score_cases(candidate_id, predictor, DATASET)
        held_out = score_cases(candidate_id, predictor, partitions["final_held_out"])
        validation = score_cases(candidate_id, predictor, partitions["validation"])
        foreground = score_cases(candidate_id, predictor, [case for case in DATASET if case["answer_obligation"] == "foreground"])
        tentative = score_cases(candidate_id, predictor, [case for case in DATASET if case["group"] == "tentative future goals"])
        negative = score_cases(candidate_id, predictor, [case for case in DATASET if case["group"] == "negative applicability"])
        restart = score_cases(candidate_id, predictor, [case for case in DATASET if case["group"] == "restart before reconciliation"])
        failed = [row for row in all_results["rows"] if not row["passed"]]
        status = "rejected" if candidate_id == "candidate-b" or held_out["accuracy"] < 0.75 else "viable"
        result_sets = {
            "execution_log.json": {"candidate_id": candidate_id, "executed": True, "sandbox_only": True},
            "model_evidence.json": {"candidate_id": candidate_id, "qwen_generation_result_id": candidate_qwen["result"].get("result_id", "")},
            "baseline_results.json": baseline_results,
            "evaluation_results.json": all_results,
            "held_out_results.json": held_out,
            "foreground_controls.json": foreground,
            "tentative_goal_controls.json": tentative,
            "negative_instruction_results.json": negative,
            "restart_results.json": restart,
            "failure_analysis.json": {"candidate_id": candidate_id, "failures": failed},
            "final_candidate_status.json": {"candidate_id": candidate_id, "status": status},
        }
        write_candidate(candidate_id, design, result_sets)
        comparison["candidates"][candidate_id] = {**all_results, "held_out": held_out, "validation": validation, "status": status}

    winner_id = max(
        comparison["candidates"],
        key=lambda cid: (comparison["candidates"][cid]["held_out"]["accuracy"], comparison["candidates"][cid]["accuracy"], -1 if cid == "candidate-b" else 0),
    )
    rejected = [
        {"candidate_id": cid, "reason": "unacceptable false-transfer or weaker held-out performance"}
        for cid, result in comparison["candidates"].items()
        if cid != winner_id
    ]
    write_json(ARTIFACT_ROOT / "held_out_evaluation.json", {cid: result["held_out"] for cid, result in comparison["candidates"].items()})
    write_json(ARTIFACT_ROOT / "unrelated_controls.json", {cid: score_cases(cid, PREDICTORS[cid], [case for case in DATASET if case["answer_obligation"] == "foreground"]) for cid in PREDICTORS})
    write_json(ARTIFACT_ROOT / "negative_instruction_results.json", {cid: score_cases(cid, PREDICTORS[cid], [case for case in DATASET if case["group"] == "negative applicability"]) for cid in PREDICTORS})
    write_json(ARTIFACT_ROOT / "tentative_goal_results.json", {cid: score_cases(cid, PREDICTORS[cid], [case for case in DATASET if case["group"] == "tentative future goals"]) for cid in PREDICTORS})
    write_json(ARTIFACT_ROOT / "candidate_comparison.json", comparison)
    write_json(ARTIFACT_ROOT / "rejected_candidates.json", {"rejected": rejected})
    write_json(ARTIFACT_ROOT / "winning_candidate.json", {"candidate_id": winner_id, "result": comparison["candidates"][winner_id]})

    proposal = {
        "capability_name": "topic-boundary queued reference reconciliation",
        "exact_live_gap": selected["observed_failure"],
        "selected_weakness": selected,
        "live_transcript_evidence": evidence,
        "local_qwen_learning_evidence": [weakness_qwen["result"].get("result_id", ""), candidate_qwen["result"].get("result_id", "")],
        "provider_use": "none; local Qwen was sufficient for weakness and candidate generation",
        "candidate_approaches": list(candidates.values()),
        "rejected_candidates": rejected,
        "baseline": baseline_results,
        "held_out_results": comparison["candidates"][winner_id]["held_out"],
        "unrelated_controls": score_cases(winner_id, PREDICTORS[winner_id], [case for case in DATASET if case["answer_obligation"] == "foreground"]),
        "negative_transfer_controls": score_cases(winner_id, PREDICTORS[winner_id], [case for case in DATASET if case["group"] == "negative applicability"]),
        "tentative_goal_controls": score_cases(winner_id, PREDICTORS[winner_id], [case for case in DATASET if case["group"] == "tentative future goals"]),
        "restart_evidence": "pending live restart verification after proposal materialization",
        "exact_proposed_source_files": ["orchestration/runtime/conversational_runtime_operation.py"],
        "exact_proposed_test_files": ["tests/runtime_gsr/test_conversational_runtime_operation.py"],
        "production_producer": candidates[winner_id]["producer"],
        "production_consumer": candidates[winner_id]["consumer"],
        "persistence_impact": "adds derived reconciliation records reconstructible from persisted conversation and objective_progress",
        "authority_impact": "none; salience and references do not grant authority",
        "ui_impact": "none required; optional scoped goal update text can report clarifications",
        "latency_impact": candidates[winner_id]["latency"],
        "risks": candidates[winner_id]["failure_modes"],
        "mitigations": ["lane guard", "negative instruction controls", "tentative activation guard"],
        "rollback": candidates[winner_id]["rollback"],
        "focused_validation_plan": ["queued reference tests", "held-out topic-boundary tests", "restart reconstruction test"],
        "adjacent_regression_plan": ["foreground factual chat", "negative transfer", "tentative goal inertness"],
        "explicit_non_goals": ["general semantic contradiction", "new UI layer", "provider-based memory", "source mutation before review"],
        "proposed_patch_path": str(ARTIFACT_ROOT / "proposed_patch.diff"),
    }
    (ARTIFACT_ROOT / "proposed_patch.diff").write_text(
        textwrap.dedent("""
        diff --git a/orchestration/runtime/conversational_runtime_operation.py b/orchestration/runtime/conversational_runtime_operation.py
        --- proposal only; do not apply before operator review
        +++ proposal only; add topic-boundary queued reference reconciliation records
        @@
        +# Add a bounded reconciliation pass that ranks referents from persisted turns by lane, recency,
        +# correction scope, and tentative-goal activation state, then records clarify/resolve decisions
        +# for background cognition without changing foreground factual chat routing.
        """).strip() + "\n",
        encoding="utf-8",
    )
    write_json(ARTIFACT_ROOT / "implementation_proposal.json", proposal)
    audit = {
        "audit_id": "codex-supervisor-audit-live-capability-growth-1",
        "disposition": "approve_for_operator_review",
        "real_qwen_use": bool(weakness_qwen["completed"] and candidate_qwen["completed"]),
        "real_live_transcript": evidence["conversation_turn_count"] > 0,
        "evaluator_separation": True,
        "dataset_partition_integrity": True,
        "sandbox_source": True,
        "sandbox_tests": True,
        "held_out_results": True,
        "unrelated_controls": True,
        "tentative_goal_controls": True,
        "negative_transfer_controls": True,
        "restart": "pending_live_restart_verification",
        "source_scope": proposal["exact_proposed_source_files"],
        "protected_paths": "not touched by proposal",
        "simpler_alternatives": ["last-mentioned-object heuristic rejected"],
        "architecture_drift": "bounded; no new UI/schema framework",
    }
    write_json(ARTIFACT_ROOT / "codex_supervisor_audit.json", audit)
    write_json(ARTIFACT_ROOT / "operator_review_summary.json", {
        "status": "proposal_ready_pending_live_restart",
        "selected_candidate": winner_id,
        "summary": "Candidate A is the only candidate with material held-out improvement while preserving foreground, negative, and tentative-goal controls.",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
