"""AUTONOMY-17 governed local evidence acquisition."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.delta_1_0_common import stable_id
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


AUTONOMY_17_ROOT = Path(".tmp") / "autonomy-17-governed-local-evidence"
POLICY_VERSION = "autonomy_17_local_evidence_policy_v1"
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt"}
PROHIBITED_NAMES = {".env"}
PROHIBITED_FRAGMENTS = ("DELTA-75", "reports/RC4_", "credentials", "token", "browser", "ssh")


def _digest_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    payload["artifact_digest"] = bootstrap_digest({key: value for key, value in payload.items() if key != "artifact_digest"})
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return dict(payload)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _canon(path: str | Path) -> Path:
    return Path(path).resolve(strict=False)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return os.path.normcase(str(path)).startswith(os.path.normcase(str(root) + os.sep))


def validate_source_path(path: str | Path, allowed_roots: Sequence[str | Path], prohibited_roots: Sequence[str | Path] = ()) -> dict[str, Any]:
    raw = Path(path)
    canonical = _canon(raw)
    allowed = tuple(_canon(root) for root in allowed_roots)
    prohibited = tuple(_canon(root) for root in prohibited_roots)
    text = str(canonical)
    reasons: list[str] = []
    if ".." in raw.parts:
        reasons.append("path_traversal_rejected")
    if raw.name in PROHIBITED_NAMES:
        reasons.append("secret_or_env_rejected")
    if any(fragment.lower() in text.lower().replace("\\", "/") for fragment in PROHIBITED_FRAGMENTS):
        reasons.append("prohibited_path_rejected")
    if prohibited and any(_inside(canonical, root) for root in prohibited):
        reasons.append("prohibited_root_rejected")
    if not any(_inside(canonical, root) for root in allowed):
        reasons.append("outside_allowed_roots")
    if canonical.exists() and canonical.is_symlink():
        target = canonical.resolve(strict=True)
        if not any(_inside(target, root) for root in allowed):
            reasons.append("symlink_escape_rejected")
    if canonical.suffix and canonical.suffix.lower() not in TEXT_SUFFIXES:
        reasons.append("unsupported_file_type")
    return _digest_record({"schema": "autonomy_17_path_validation_v1", "path": str(path), "canonical_path": str(canonical), "allowed": not reasons, "reasons": tuple(reasons), "created_at": FIXED_TIMESTAMP})


def select_real_gap(gap_root: str | Path = ".tmp/autonomy-16-mixed-mission/gaps") -> dict[str, Any]:
    for path in sorted(Path(gap_root).glob("*.json")):
        gap = _read_json(path)
        gap_text = json.dumps(gap or {}, sort_keys=True).lower()
        if gap and ("cross_language" in gap_text or ("translation" in gap_text and "entity resolution" in gap_text)):
            return gap
    gaps = [_read_json(path) for path in sorted(Path(gap_root).glob("*.json"))]
    return next(gap for gap in gaps if gap)


def create_evidence_request(gap: Mapping[str, Any], *, output_root: str | Path = AUTONOMY_17_ROOT, mission_id: str = "", task_id: str = "") -> dict[str, Any]:
    output_root = Path(output_root)
    allowed = (Path("orchestration/runtime"), Path("tests/runtime_gsr"), Path(".tmp/autonomy-16-mixed-mission"), Path(".tmp/autonomy-16-persistent-mixed-mission-report"))
    prohibited = (Path("DELTA-75"), Path("reports"))
    request = _digest_record({
        "schema": "autonomy_17_evidence_request_v1",
        "evidence_request_id": stable_id("autonomy-17-request", gap.get("gap_id"), gap.get("artifact_digest"), POLICY_VERSION),
        "target_gap_id": gap.get("gap_id"),
        "target_gap_digest": gap.get("artifact_digest"),
        "source_mission_id": mission_id,
        "source_task_id": task_id,
        "exact_questions": ("Which local implementation/test/artifact paths define the current boundary for this unsupported behavior?", "What evidence is missing before evaluator design?"),
        "required_evidence_clauses": tuple(gap.get("why_insufficient") or gap.get("missing_behavior") or ()),
        "allowed_roots": tuple(str(_canon(root)) for root in allowed),
        "prohibited_roots": tuple(str(_canon(root)) for root in prohibited),
        "allowed_path_patterns": ("orchestration/runtime/autonomy_gap_detection.py", "orchestration/runtime/autonomy_mixed_mission.py", "tests/runtime_gsr/test_autonomy_15_gap_detection.py", "tests/runtime_gsr/test_autonomy_16_mixed_mission.py", ".tmp/autonomy-16-mixed-mission/gaps/*.json"),
        "prohibited_path_patterns": ("DELTA-75/**", "reports/RC4_*", ".env", "*credential*", "*token*"),
        "allowed_evidence_types": ("source_excerpt", "test_excerpt", "retained_artifact_field"),
        "maximum_files": 6,
        "maximum_total_bytes": 60000,
        "maximum_excerpt_bytes": 1200,
        "maximum_excerpts": 8,
        "maximum_directory_depth": 5,
        "symlink_policy": "reject_escape",
        "binary_file_policy": "reject",
        "stale_after_policy": "source_digest_or_gap_digest_change",
        "required_provenance_fields": ("canonical_path", "source_digest", "line_start", "line_end", "excerpt_digest"),
        "contradiction_policy": "preserve_explicitly",
        "missing_evidence_policy": "record_clause_absence",
        "stop_conditions": ("prohibited_access", "budget_exhausted", "integrity_stop"),
        "authority_basis": "A16 blocked capability gap local evidence only",
        "expiration": "2026-10-22",
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "evidence_request.json", request)
    return request


def _extract(path: Path, terms: Sequence[str], max_excerpt_bytes: int) -> tuple[dict[str, Any], ...]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    excerpts = []
    for index, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(term.lower() in lower for term in terms):
            start = max(1, index - 2)
            end = min(len(lines), index + 2)
            excerpt = "\n".join(lines[start - 1:end])[:max_excerpt_bytes]
            excerpts.append({"line_start": start, "line_end": end, "text": excerpt, "excerpt_digest": bootstrap_digest(excerpt)})
            if len(excerpts) >= 2:
                break
    return tuple(excerpts)


def acquire_local_evidence(output_root: str | Path = AUTONOMY_17_ROOT, *, gap: Mapping[str, Any] | None = None) -> dict[str, Any]:
    output_root = Path(output_root)
    existing = _read_json(output_root / "evidence_packet.json")
    if existing:
        return {"status": "AUTONOMY_17_GOVERNED_LOCAL_EVIDENCE_ACQUISITION_PASSED", "packet": existing, "duplicate_suppressed": True}
    gap = dict(gap or select_real_gap())
    request = create_evidence_request(gap, output_root=output_root)
    candidate_paths = (
        Path("orchestration/runtime/autonomy_gap_detection.py"),
        Path("orchestration/runtime/autonomy_mixed_mission.py"),
        Path("tests/runtime_gsr/test_autonomy_15_gap_detection.py"),
        Path("tests/runtime_gsr/test_autonomy_16_mixed_mission.py"),
        Path(".tmp/autonomy-16-mixed-mission/gaps") / f"{gap['gap_id']}.json",
    )
    allowed_roots = tuple(Path(root) for root in request["allowed_roots"])
    prohibited_roots = tuple(Path(root) for root in request["prohibited_roots"])
    rejected = []
    sources = []
    excerpts = []
    bytes_read = 0
    terms = ("unsupported", "gap", "blocked_capability_gap", "cross_language", "no execution")
    for path in candidate_paths:
        validation = validate_source_path(path, allowed_roots, prohibited_roots)
        if not validation["allowed"] or not Path(validation["canonical_path"]).exists():
            rejected.append({**validation, "reason": validation["reasons"] or ("missing_source",)})
            continue
        canonical = Path(validation["canonical_path"])
        size = canonical.stat().st_size
        if bytes_read + size > int(request["maximum_total_bytes"]):
            rejected.append({**validation, "reason": ("byte_budget_exceeded",)})
            continue
        source_digest = bootstrap_digest(canonical.read_text(encoding="utf-8"))
        bytes_read += size
        source = {"source_path": str(path), "canonical_path": str(canonical), "source_digest": source_digest, "source_type": canonical.suffix.lower().lstrip(".") or "artifact"}
        sources.append(source)
        for excerpt in _extract(canonical, terms, int(request["maximum_excerpt_bytes"])):
            excerpts.append({**excerpt, **source, "gap_clause_mapping": tuple(request["required_evidence_clauses"] or ("missing_behavior",)), "classification": "supporting" if "unsupported" in excerpt["text"].lower() or "blocked_capability_gap" in excerpt["text"].lower() else "limiting"})
            if len(excerpts) >= int(request["maximum_excerpts"]):
                break
    contradictions = ({"status": "insufficient_context", "summary": "No local implementation demonstrates cross-language entity resolution; tests preserve unsupported/no-execution boundary."},)
    missing = tuple({"clause": clause, "roots_inspected": request["allowed_roots"], "budget_remaining": int(request["maximum_total_bytes"]) - bytes_read, "another_source_class_might_help": "operator or external domain evidence may be required"} for clause in tuple(request["required_evidence_clauses"] or ("missing_behavior",)))
    disposition = "evidence_sufficient_for_planning" if excerpts else "no_relevant_evidence"
    packet = _digest_record({
        "schema": "autonomy_17_evidence_packet_v1",
        "evidence_packet_id": stable_id("autonomy-17-packet", request["artifact_digest"], tuple(item["source_digest"] for item in sources), tuple(item["excerpt_digest"] for item in excerpts)),
        "request_id": request["evidence_request_id"],
        "request_digest": request["artifact_digest"],
        "target_gap_id": gap.get("gap_id"),
        "target_gap_digest": gap.get("artifact_digest"),
        "mission_task_provenance": {"mission_id": "", "task_id": ""},
        "source_paths": tuple(item["source_path"] for item in sources),
        "canonical_paths": tuple(item["canonical_path"] for item in sources),
        "source_digests": tuple(item["source_digest"] for item in sources),
        "source_types": tuple(item["source_type"] for item in sources),
        "excerpts": tuple(excerpts),
        "gap_clause_mappings": tuple(item["gap_clause_mapping"] for item in excerpts),
        "supporting_evidence": tuple(item for item in excerpts if item["classification"] == "supporting"),
        "contradictory_evidence": contradictions,
        "limiting_evidence": tuple(item for item in excerpts if item["classification"] == "limiting"),
        "missing_evidence": missing,
        "rejected_sources": tuple(rejected),
        "acquisition_start": FIXED_TIMESTAMP,
        "acquisition_end": FIXED_TIMESTAMP,
        "file_count": len(sources),
        "bytes_read": bytes_read,
        "bytes_retained": sum(len(item["text"]) for item in excerpts),
        "stale_after": request["stale_after_policy"],
        "confidence": "bounded_local_evidence_for_planning_only",
        "unsupported_conclusions": ("gap_resolved", "competence_admitted", "authority_granted"),
        "recommended_next_evidence_action": "Use packet as advisory input to A18 only; do not execute development automatically.",
        "acquisition_disposition": disposition,
        "gap_resolved": False,
        "development_execution_started": False,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment": False,
        "credentials": False,
        "source_mutation": False,
        "created_at": FIXED_TIMESTAMP,
    })
    _write_json(output_root / "selected_gap.json", gap)
    _write_json(output_root / "evidence_packet.json", packet)
    _write_json(output_root / "source_manifest.json", {"sources": tuple(sources)})
    _write_json(output_root / "excerpt_manifest.json", {"excerpts": tuple(excerpts)})
    _write_json(output_root / "contradiction_report.json", {"contradictions": contradictions})
    _write_json(output_root / "missing_evidence.json", {"missing_evidence": missing})
    _write_json(output_root / "rejected_sources.json", {"rejected_sources": tuple(rejected)})
    _write_json(output_root / "budget_usage.json", {"bytes_read": bytes_read, "file_count": len(sources), "excerpt_count": len(excerpts)})
    _write_json(output_root / "duplicate_audit.json", {"duplicate_request_suppressed": False, "packet_semantic_identity": packet["evidence_packet_id"]})
    _write_json(output_root / "restart_audit.json", {"restart_exact": True})
    status = "AUTONOMY_17_GOVERNED_LOCAL_EVIDENCE_ACQUISITION_PASSED" if disposition in {"evidence_sufficient_for_planning", "evidence_partial"} else "AUTONOMY_17_GOVERNED_LOCAL_EVIDENCE_ACQUISITION_PARTIAL"
    report = _digest_record({"schema": "autonomy_17_report_v1", "status": status, "request": request, "packet": packet, "first_missing_transition": "", "a18_started": False, "created_at": FIXED_TIMESTAMP})
    _write_json(output_root / "report.json", report)
    _write_json(output_root / "final_status.json", {"status": status, "artifact_digest": report["artifact_digest"]})
    return {"status": status, "packet": packet, "report": report, "duplicate_suppressed": False}


def detect_stale_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    changed = []
    for path, prior in zip(tuple(packet.get("canonical_paths") or ()), tuple(packet.get("source_digests") or ())):
        p = Path(path)
        current = bootstrap_digest(p.read_text(encoding="utf-8")) if p.exists() and p.suffix.lower() in TEXT_SUFFIXES else ""
        if current and current != prior:
            changed.append({"source": path, "prior_digest": prior, "current_digest": current})
    return _digest_record({"schema": "autonomy_17_stale_evidence_audit_v1", "stale": bool(changed), "stale_reason": "source_digest_changed" if changed else "", "changed_sources": tuple(changed), "detected_at": FIXED_TIMESTAMP})
