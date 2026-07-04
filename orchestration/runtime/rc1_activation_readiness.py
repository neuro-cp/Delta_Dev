"""RC1 activation-readiness planning.

This module is deliberately report-only. It maps the next possible activation
steps after RC1 adversarial validation without enabling providers, live
ingestion, training, memory mutation, knowledge mutation, schedulers, or action
execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


MATRIX_JSON = Path("reports/runtime_rc1_activation_readiness_matrix.json")
MATRIX_MD = Path("reports/runtime_rc1_activation_readiness_matrix.md")
WAVE_JSON = Path("reports/runtime_rc1_activation_wave_plan.json")
WAVE_MD = Path("reports/runtime_rc1_activation_wave_plan.md")
FIRST_JSON = Path("reports/runtime_rc1_first_activation_candidate.json")
FIRST_MD = Path("reports/runtime_rc1_first_activation_candidate.md")


SAFETY_FLAGS: dict[str, bool | str] = {
    "model_b_default": "unchanged",
    "hyb1": "dormant_env_gated",
    "training_performed": False,
    "fine_tuning_performed": False,
    "model_update_performed": False,
    "provider_authority_granted": False,
    "provider_call_performed": False,
    "autonomous_browsing_performed": False,
    "autonomous_execution_performed": False,
    "scheduler_started": False,
    "background_worker_started": False,
    "memory_mutation_performed": False,
    "knowledge_mutation_performed": False,
    "hidden_write_performed": False,
}


@dataclass(frozen=True)
class ActivationCapability:
    capability: str
    current_status: str
    required_gates: tuple[str, ...]
    required_tests: tuple[str, ...]
    required_fixtures: tuple[str, ...]
    safety_risks: tuple[str, ...]
    rollback_requirement: str
    audit_requirement: str
    activation_order: int
    recommended_first_activation_state: str

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in ("required_gates", "required_tests", "required_fixtures", "safety_risks"):
            data[key] = list(data[key])
        return data


@dataclass(frozen=True)
class ActivationWave:
    wave: int
    name: str
    purpose: str
    capabilities: tuple[str, ...]
    entry_criteria: tuple[str, ...]
    exit_criteria: tuple[str, ...]
    hard_blockers: tuple[str, ...]
    required_tests: tuple[str, ...]
    safety_gates: tuple[str, ...]
    manual_smoke_commands: tuple[str, ...]
    rollback_procedure: str
    stop_conditions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        for key in (
            "capabilities",
            "entry_criteria",
            "exit_criteria",
            "hard_blockers",
            "required_tests",
            "safety_gates",
            "manual_smoke_commands",
            "stop_conditions",
        ):
            data[key] = list(data[key])
        return data


def build_activation_matrix() -> dict[str, Any]:
    records = (
        ActivationCapability(
            "live document adapter",
            "disabled; adversarial validation flagged live_document_adapter_disabled_fixture_only",
            ("manual RC1 validation", "fixture parser parity", "no persistence by default"),
            ("document adapter fixture tests", "malformed document tests", "provenance-required tests"),
            ("small text fixture folder", "contradictory document fixture", "missing provenance fixture"),
            ("unbounded input size", "provenance loss", "accidental persistence"),
            "delete generated fixture outputs; no canonical rollback needed before persistence",
            "append adapter trace with source hash, parser version, and no-write proof",
            1,
            "fixture_only",
        ),
        ActivationCapability(
            "real corpus ingestion",
            "disabled; no live ingestion path is authorized",
            ("admin approval", "input folder allowlist", "dry-run manifest", "size cap"),
            ("ingestion dry-run tests", "corpus manifest validation", "secret redaction tests"),
            ("approved local corpus fixture", "oversized corpus fixture", "unsupported file fixture"),
            ("secret exposure", "unbounded storage growth", "provider-like authority from raw text"),
            "delete noncanonical ingestion workspace by run id",
            "manifest, hashes, skipped files, parser warnings, and zero canonical writes",
            6,
            "admin_gated",
        ),
        ActivationCapability(
            "semantic record persistence",
            "disabled outside simulated E2E harness",
            ("fixture-only semantic output folder", "schema validation", "noncanonical namespace"),
            ("semantic schema tests", "duplicate record tests", "noncanonical path tests"),
            ("Project Atlas semantic fixture", "duplicate semantic fixture"),
            ("mistaking records for truth", "schema drift", "duplicate semantic amplification"),
            "remove semantic output folder by run id",
            "record provenance, source hash, schema version, and noncanonical status",
            2,
            "dry_run",
        ),
        ActivationCapability(
            "replay batch persistence",
            "disabled; replay is scaffolded and simulated",
            ("semantic record dry-run complete", "batch manifest", "no scheduler"),
            ("replay batch schema tests", "idempotence tests", "no scheduler tests"),
            ("small semantic record set", "empty replay fixture"),
            ("background worker creep", "duplicate batch creation", "ordering mistakes"),
            "delete replay batch workspace by run id",
            "batch id, source records, deterministic ordering, and scheduler-disabled proof",
            3,
            "dry_run",
        ),
        ActivationCapability(
            "consolidation candidate persistence",
            "disabled; candidates are report-only/simulated",
            ("replay batch dry-run complete", "review state starts pending", "no integration"),
            ("candidate schema tests", "review-state tests", "no write-to-canonical tests"),
            ("candidate fixture from replay batch", "contradictory candidate fixture"),
            ("candidate treated as knowledge", "review bypass", "premature confidence"),
            "delete candidate workspace by run id",
            "candidate provenance, review state, supporting and opposing evidence",
            4,
            "dry_run",
        ),
        ActivationCapability(
            "approval-gated substrate write",
            "disabled; previous trials require exact structured approval and remain local",
            ("exact approval phrase", "overwatch allow or owner override", "rollback token"),
            ("approval parser tests", "overwatch-block tests", "rollback reference tests"),
            ("single candidate fixture", "approval denial fixture"),
            ("casual approval inference", "bulk approval", "irreversible write"),
            "rollback token must remove or mark inactive the trial record",
            "admin approval event, overwatch result, target store, rollback token",
            8,
            "owner_override_only",
        ),
        ActivationCapability(
            "read-only substrate retrieval",
            "available as deterministic RC1 query adapter over fixtures",
            ("read-only adapter", "no recall mutation", "grounding required"),
            ("query adapter tests", "no mutation tests", "unsupported query tests"),
            ("ARC II sample substrate", "RC1 document audit slice", "E2E consolidated fixture"),
            ("overstating fixture coverage", "using missing evidence as proof"),
            "not applicable; read-only outputs can be discarded",
            "query packet with source object ids and missing evidence list",
            5,
            "read_only",
        ),
        ActivationCapability(
            "grounded answer synthesis",
            "available locally for deterministic repo/self-description and fixture answers",
            ("evidence packet", "uncertainty note", "no provider fallback unless gated"),
            ("grounding tests", "unknown-answer tests", "no provider-call tests"),
            ("Project Atlas answer fixture", "unsupported local question fixture"),
            ("confident unsupported answer", "fixture answer mistaken for world answer"),
            "not applicable; response-only",
            "answer envelope with evidence ids, uncertainty, and safety flags",
            5,
            "read_only",
        ),
        ActivationCapability(
            "provider-assisted evidence",
            "disabled; provider authority and calls remain off",
            ("explicit admin gate", "cost limit", "evidence-only status", "overwatch review"),
            ("provider gate tests", "mock-provider tests", "no authority tests"),
            ("mock provider fixture", "blocked provider fixture"),
            ("provider treated as truth", "cost runaway", "secret leakage"),
            "discard provider evidence candidate; no knowledge rollback before integration",
            "provider, model, prompt hash, response hash, token/cost, evidence-only state",
            10,
            "overwatch_gated",
        ),
        ActivationCapability(
            "specialist deliberation",
            "dormant/advisory; specialists remain non-authoritative",
            ("specialist outputs advisory only", "disagreement capture", "no routing authority"),
            ("specialist disagreement tests", "advisory-only tests"),
            ("conflicting specialist fixture", "empty specialist fixture"),
            ("authority transfer", "consensus mistaken for truth"),
            "discard advisory bundle by run id",
            "specialist role, claim, evidence, disagreement, advisory-only marker",
            11,
            "overwatch_gated",
        ),
        ActivationCapability(
            "graph repair",
            "report-only; adversarial validation flagged graph_repair_is_report_only",
            ("repair preview only", "human review", "rollback plan before mutation"),
            ("corrupt graph report tests", "circular graph tests", "no mutation tests"),
            ("corrupted graph fixture", "circular graph fixture"),
            ("silent edge deletion", "relationship rewrite", "repair-as-truth"),
            "restore previous graph snapshot or discard repair preview",
            "damage report, proposed repair diff, risk score, rollback reference",
            9,
            "dry_run",
        ),
        ActivationCapability(
            "executive planning",
            "non-executing; adversarial validation bounded this pathology",
            ("planning-only flag", "no action binding", "review before execution"),
            ("planning-only tests", "no execution tests", "constraint tests"),
            ("resource allocation fixture", "conflicting goal fixture"),
            ("plan mistaken for action", "unsafe recommendation under uncertainty"),
            "discard transient plan; no external side effects",
            "goal, constraints, plan alternatives, risks, review state",
            7,
            "read_only",
        ),
        ActivationCapability(
            "rollback execution",
            "disabled; rollback references exist but do not execute",
            ("trial write exists", "exact rollback approval", "pre/post audit"),
            ("rollback simulation tests", "rollback authorization tests"),
            ("single trial write fixture", "rollback-denied fixture"),
            ("wrong target rollback", "unreviewed destructive action"),
            "rollback itself must create a compensating audit record",
            "rollback token, target, approver, before/after status",
            9,
            "admin_gated",
        ),
        ActivationCapability(
            "evaluation/regression loop",
            "manual test/report loop active; schedulers disabled",
            ("manual invocation", "fixed fixtures", "no scheduler"),
            ("regression harness tests", "no scheduler tests", "JSON validation"),
            ("RC1 manual scenario pack", "adversarial scenario pack"),
            ("metrics treated as authority", "background execution creep"),
            "discard report outputs or compare against previous run",
            "test count, JSON validation, safety flags, scenario deltas",
            0,
            "read_only",
        ),
        ActivationCapability(
            "sleep/replay consolidation",
            "design/scaffold only; no scheduled consolidation",
            ("manual batch", "review-only consolidation", "no scheduler", "no canonical write"),
            ("sleep plan tests", "manual replay tests", "no mutation tests"),
            ("small replay batch fixture", "conflicting replay fixture"),
            ("scheduler activation", "autonomous learning", "silent consolidation"),
            "discard sleep-cycle plan and noncanonical batch workspace",
            "batch id, review result, consolidation decision, no-write proof",
            3,
            "dry_run",
        ),
    )
    return {
        "phase": "RC1 Activation Readiness Matrix",
        "current_checkpoint": "3c0a05a",
        "runtime_maturity_estimate": 97,
        "capabilities": [record.as_dict() for record in records],
        "recommended_first_activation_candidate": "fixture-only corpus ingestion into noncanonical semantic records",
        "safety": SAFETY_FLAGS,
        "final_recommendation": "PROCEED_MANUAL_RC1_VALIDATION_NO_LIVE_CAPABILITIES",
    }


def build_activation_wave_plan() -> dict[str, Any]:
    waves = (
        ActivationWave(
            0,
            "manual RC1 validation only",
            "Confirm the deterministic RC1 surfaces behave as claimed before enabling any live-ish capability.",
            ("evaluation/regression loop", "grounded answer synthesis", "read-only substrate retrieval"),
            ("RC1 adversarial validation passed", "worktree clean or intentional changes only"),
            ("manual script passes", "operator reviews readiness and safety outputs"),
            ("any provider call", "any memory/knowledge mutation", "any scheduler start"),
            ("tests/runtime_rc1/test_rc1_manual_validation.py", "existing RC1 adversarial tests"),
            ("no-live-capabilities", "read-only reports", "manual invocation"),
            (
                r".\.venv311\Scripts\python.exe scripts\delta_rc1_manual_validation.py",
                r".\.venv311\Scripts\python.exe scripts\delta_answer.py ""What does RC1 readiness mean?""",
            ),
            "No rollback needed; discard generated manual validation output if desired.",
            ("manual validation exits nonzero", "safety flag changes", "unexpected file/network/provider activity"),
        ),
        ActivationWave(
            1,
            "fixture corpus ingestion and semantic records",
            "Exercise parser and semantic-record shape on local fixtures only.",
            ("live document adapter", "semantic record persistence"),
            ("Wave 0 passed", "fixture folder allowlisted", "noncanonical output folder selected"),
            ("fixture manifest generated", "semantic records validate", "no canonical writes"),
            ("input outside allowlist", "secret-like content detected", "canonical target requested"),
            ("document parser fixture tests", "semantic schema tests", "secret scan"),
            ("fixture-only", "noncanonical namespace", "no provider calls"),
            (r".\.venv311\Scripts\python.exe scripts\delta_rc1_fixture_ingest.py --dry-run <fixture_dir>",),
            "Delete the noncanonical fixture output folder by run id.",
            ("schema validation failure", "unexpected persistence target", "provenance missing"),
        ),
        ActivationWave(
            2,
            "read-only retrieval and grounded synthesis",
            "Query noncanonical fixture records and synthesize grounded answers without mutating recall.",
            ("read-only substrate retrieval", "grounded answer synthesis"),
            ("Wave 1 passed", "fixture records validated"),
            ("answers cite fixture record ids", "unsupported questions abstain", "recall remains unmutated"),
            ("unsupported confident answer", "recall mutation", "provider fallback"),
            ("query adapter tests", "grounding tests", "unknown-answer tests"),
            ("read-only", "candidate-context only", "uncertainty required"),
            (r".\.venv311\Scripts\python.exe scripts\delta_rc1_query_fixture.py ""What did the fixture say?""",),
            "Discard response/report outputs only.",
            ("hallucinated evidence", "missing uncertainty", "mutation flag changes"),
        ),
        ActivationWave(
            3,
            "approval-gated simulated substrate writes",
            "Allow a single explicitly approved simulated write into a noncanonical trial store.",
            ("approval-gated substrate write",),
            ("Wave 2 passed", "single candidate selected", "exact approval phrase present"),
            ("one trial record written", "audit metadata exists", "rollback token exists"),
            ("casual approval accepted", "bulk write", "canonical target"),
            ("approval parser tests", "trial write tests", "rollback reference tests"),
            ("admin-gated", "overwatch-gated unless owner override", "single candidate only"),
            (r".\.venv311\Scripts\python.exe scripts\delta_controlled_memory_write.py --candidate <id>",),
            "Use rollback token to mark trial record inactive or delete trial workspace.",
            ("approval ambiguity", "overwatch block without owner override", "missing rollback token"),
        ),
        ActivationWave(
            4,
            "rollback and evaluation validation",
            "Prove trial writes can be reversed and evaluated without side effects.",
            ("rollback execution", "evaluation/regression loop", "graph repair"),
            ("Wave 3 passed", "rollback token present", "pre-rollback audit complete"),
            ("rollback simulation passes", "post-rollback evaluation passes", "no destructive action"),
            ("rollback target mismatch", "unapproved destructive operation", "regression failure"),
            ("rollback authorization tests", "evaluation regression tests", "graph repair report tests"),
            ("admin-gated rollback", "report-only graph repair", "manual evaluation"),
            (r".\.venv311\Scripts\python.exe scripts\delta_rollback_simulation.py --token <rollback_token>",),
            "Restore prior trial store state or discard trial workspace.",
            ("rollback changes canonical store", "evaluation starts scheduler", "audit incomplete"),
        ),
        ActivationWave(
            5,
            "provider-assisted evidence, gated",
            "Use providers only as explicit evidence acquisition, never authority.",
            ("provider-assisted evidence", "specialist deliberation"),
            ("Wave 4 passed", "API/key gate explicit", "cost cap", "overwatch enabled"),
            ("provider result stored as evidence candidate only", "no authority transfer", "cost logged"),
            ("provider answer treated as truth", "provider called without approval", "secret printed"),
            ("provider gate tests", "mock/live parity tests", "secret scan"),
            ("overwatch-gated", "evidence-only", "cost-capped"),
            (r".\.venv311\Scripts\python.exe scripts\delta_provider_to_candidate.py --approved --dry-run",),
            "Discard provider evidence candidate; no canonical rollback before integration.",
            ("provider call without approval", "authority flag true", "secret leakage"),
        ),
        ActivationWave(
            6,
            "controlled live corpus pilot",
            "Run a small allowlisted local corpus through ingestion, retrieval, and review.",
            ("real corpus ingestion", "semantic record persistence", "read-only substrate retrieval"),
            ("Wave 5 optional or skipped", "local corpus allowlist", "operator approval"),
            ("bounded corpus manifest", "semantic outputs validated", "manual review complete"),
            ("unbounded corpus", "secret content", "canonical write"),
            ("corpus pilot tests", "manifest validation", "storage cap tests"),
            ("admin-gated", "noncanonical", "rollback-by-workspace-delete"),
            (r".\.venv311\Scripts\python.exe scripts\delta_live_corpus_pilot.py --dry-run --input <allowlisted_dir>",),
            "Delete pilot workspace by run id.",
            ("storage cap exceeded", "provenance missing", "mutation outside workspace"),
        ),
        ActivationWave(
            7,
            "limited learning/consolidation pilot",
            "Run manual replay/consolidation over pilot records without autonomous learning.",
            ("replay batch persistence", "consolidation candidate persistence", "sleep/replay consolidation"),
            ("Wave 6 passed", "manual replay batch selected", "review path ready"),
            ("candidates are reviewable", "decisions stay noncanonical", "no scheduler"),
            ("autonomous consolidation", "canonical write", "scheduler activation"),
            ("replay tests", "consolidation candidate tests", "no canonical write tests"),
            ("manual-only", "dry-run", "review-required"),
            (r".\.venv311\Scripts\python.exe scripts\delta_sleep_replay_plan.py --manual-batch <batch_id>",),
            "Discard replay/consolidation workspace by run id.",
            ("batch duplication", "silent integration", "mutation flag changes"),
        ),
    )
    return {
        "phase": "RC1 Activation Wave Plan",
        "waves": [wave.as_dict() for wave in waves],
        "safety": SAFETY_FLAGS,
        "final_recommendation": "PROCEED_WAVE_0_MANUAL_RC1_VALIDATION",
    }


def build_first_activation_candidate() -> dict[str, Any]:
    return {
        "phase": "RC1 First Activation Candidate",
        "candidate": "fixture-only corpus ingestion into noncanonical semantic records",
        "do_not_activate_in_this_run": True,
        "why_safest": (
            "It exercises the live-document-adapter bottleneck with local fixtures only, writes only to a "
            "noncanonical run workspace, requires no providers, and can be rolled back by deleting the run folder."
        ),
        "exact_command_design": r".\.venv311\Scripts\python.exe scripts\delta_rc1_fixture_ingest.py --dry-run --input fixtures\rc1_corpus --output .tmp\rc1_activation\semantic_records",
        "input_folder": "fixtures/rc1_corpus",
        "output_folder": ".tmp/rc1_activation/semantic_records/<run_id>",
        "safety_flags": (
            "fixture_only=true",
            "canonical_write_enabled=false",
            "provider_calls_enabled=false",
            "training_enabled=false",
            "scheduler_enabled=false",
            "memory_mutation_enabled=false",
        ),
        "approval_requirements": (
            "manual operator command invocation",
            "allowlisted input folder",
            "noncanonical output folder",
            "no bulk canonical approval",
        ),
        "rollback_strategy": "Delete the noncanonical run output folder and preserve its manifest in reports if needed.",
        "tests_required_before_activation": (
            "parser handles malformed fixture without crash",
            "semantic records include provenance and source hash",
            "output path is noncanonical",
            "no provider/training/scheduler/memory/knowledge mutation flags change",
            "secret scan passes on generated records",
        ),
        "manual_acceptance_criteria": (
            "operator can inspect manifest",
            "each semantic record points to a fixture source",
            "unsupported or malformed documents are skipped with warnings",
            "no generated record is treated as canonical knowledge",
        ),
        "safety": SAFETY_FLAGS,
        "final_recommendation": "PROCEED_WAVE_0_MANUAL_RC1_VALIDATION_FIRST",
    }


def _write_json_markdown(payload: dict[str, Any], json_path: Path, md_path: Path, title: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_render_markdown(payload, title), encoding="utf-8")


def _render_markdown(payload: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", ""]
    lines.append(f"- phase: {payload.get('phase')}")
    if "runtime_maturity_estimate" in payload:
        lines.append(f"- runtime_maturity_estimate: {payload['runtime_maturity_estimate']}%")
    lines.append(f"- final_recommendation: `{payload.get('final_recommendation')}`")
    lines.append("")
    if "capabilities" in payload:
        lines.extend(["## Capability Matrix", ""])
        lines.append("| Capability | Status | First State | Order | Key Gates |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in payload["capabilities"]:
            gates = "; ".join(item["required_gates"])
            lines.append(
                f"| {item['capability']} | {item['current_status']} | {item['recommended_first_activation_state']} | {item['activation_order']} | {gates} |"
            )
    if "waves" in payload:
        lines.extend(["## Activation Waves", ""])
        for wave in payload["waves"]:
            lines.append(f"### Wave {wave['wave']}: {wave['name']}")
            lines.append(f"- purpose: {wave['purpose']}")
            lines.append(f"- capabilities: {', '.join(wave['capabilities'])}")
            lines.append(f"- entry criteria: {'; '.join(wave['entry_criteria'])}")
            lines.append(f"- exit criteria: {'; '.join(wave['exit_criteria'])}")
            lines.append(f"- stop conditions: {'; '.join(wave['stop_conditions'])}")
            lines.append("")
    if "candidate" in payload:
        lines.extend(
            [
                "## Candidate",
                "",
                f"- candidate: {payload['candidate']}",
                f"- do_not_activate_in_this_run: {payload['do_not_activate_in_this_run']}",
                f"- command design: `{payload['exact_command_design']}`",
                f"- input folder: `{payload['input_folder']}`",
                f"- output folder: `{payload['output_folder']}`",
                "",
                "## Why Safest",
                "",
                str(payload["why_safest"]),
                "",
                "## Tests Required Before Activation",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in payload["tests_required_before_activation"])
    lines.extend(["", "## Safety", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["safety"].items()))
    lines.append("")
    return "\n".join(lines)


def write_activation_readiness_reports() -> dict[str, Any]:
    matrix = build_activation_matrix()
    waves = build_activation_wave_plan()
    first = build_first_activation_candidate()
    _write_json_markdown(matrix, MATRIX_JSON, MATRIX_MD, "RC1 Activation Readiness Matrix")
    _write_json_markdown(waves, WAVE_JSON, WAVE_MD, "RC1 Activation Wave Plan")
    _write_json_markdown(first, FIRST_JSON, FIRST_MD, "RC1 First Activation Candidate")
    return {"matrix": matrix, "waves": waves, "first_activation_candidate": first}


if __name__ == "__main__":
    written = write_activation_readiness_reports()
    print(written["matrix"]["final_recommendation"])
    print(written["waves"]["final_recommendation"])
    print(written["first_activation_candidate"]["final_recommendation"])
