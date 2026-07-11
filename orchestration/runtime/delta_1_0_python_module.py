"""Python Coding Module v1 for DELTA 1.0.

The module performs deterministic repository understanding and prepares inert
proposal artifacts. It never executes commands, applies patches, installs
packages, commits, pushes, calls providers, or writes outside explicit report
generation performed by operator-invoked tooling.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id


DEFAULT_IGNORES = (
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "reports",
    "data",
    "dist",
    "build",
)

MAX_FILE_BYTES = 512_000


@dataclass(frozen=True)
class PythonSymbol:
    name: str
    kind: str
    file: str
    line: int
    decorators: tuple[str, ...] = ()
    calls: tuple[str, ...] = ()
    is_async: bool = False


@dataclass(frozen=True)
class PythonImport:
    module: str
    imported_name: str | None
    file: str
    line: int
    relative: bool = False


@dataclass(frozen=True)
class PythonFileRecord:
    path: str
    package: str
    bytes: int
    symbols: tuple[PythonSymbol, ...]
    imports: tuple[PythonImport, ...]
    tests: tuple[str, ...]
    side_effect_indicators: tuple[str, ...]
    parse_error: str | None = None
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PythonRepositoryIndex:
    root: str
    files: tuple[PythonFileRecord, ...]
    packages: tuple[str, ...]
    import_graph: dict[str, tuple[str, ...]]
    symbol_index: dict[str, tuple[str, ...]]
    test_map: dict[str, tuple[str, ...]]
    skipped: tuple[str, ...]
    uncertainty: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class BoundedChangeRequest:
    request_id: str
    summary: str
    target_paths: tuple[str, ...]
    constraints: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ImplementationProposal:
    proposal_id: str
    request_id: str
    affected_files: tuple[str, ...]
    rationale_summary: str
    proposed_steps: tuple[str, ...]
    validation_plan: tuple[str, ...]
    risk_notes: tuple[str, ...]
    authority: str = "proposal_only"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PatchProposal:
    patch_id: str
    proposal_id: str
    files: tuple[str, ...]
    diff_preview: str
    applies_automatically: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class FailureInterpretation:
    failure_id: str
    failure_class: str
    likely_causes: tuple[str, ...]
    evidence_needed: tuple[str, ...]
    bounded_next_steps: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class ValidationPlan:
    plan_id: str
    commands_to_request_from_operator: tuple[str, ...]
    focused_tests: tuple[str, ...]
    static_checks: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    executes_now: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def analyze_python_repository(root: Path, *, max_files: int = 800) -> PythonRepositoryIndex:
    resolved = root.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError("approved root must be an existing directory")
    records: list[PythonFileRecord] = []
    skipped: list[str] = []
    for path in sorted(resolved.rglob("*.py")):
        if len(records) >= max_files:
            skipped.append("max_files_reached")
            break
        rel = _safe_relative(resolved, path)
        if _ignored(rel):
            skipped.append(rel)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            skipped.append(f"{rel}:stat_failed")
            continue
        if size > MAX_FILE_BYTES:
            skipped.append(f"{rel}:too_large")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        records.append(_analyze_file(resolved, path, rel, text, size))
    packages = tuple(sorted({_package_for(record.path) for record in records if _package_for(record.path)}))
    import_graph = _build_import_graph(records)
    symbol_index = _build_symbol_index(records)
    test_map = _build_test_map(records)
    uncertainty = tuple(sorted({record.parse_error for record in records if record.parse_error}))
    return PythonRepositoryIndex(
        root=str(resolved),
        files=tuple(records),
        packages=packages,
        import_graph=import_graph,
        symbol_index=symbol_index,
        test_map=test_map,
        skipped=tuple(skipped),
        uncertainty=uncertainty,
    )


def build_change_request(summary: str, target_paths: tuple[str, ...], *, root: Path | None = None) -> BoundedChangeRequest:
    normalized_targets: list[str] = []
    for target in target_paths:
        if ".." in Path(target).parts or Path(target).is_absolute():
            raise ValueError("target paths must be relative and within approved root")
        if root is not None:
            _safe_relative(root.resolve(), (root / target).resolve())
        normalized_targets.append(target.replace("\\", "/"))
    return BoundedChangeRequest(
        request_id=stable_id("python-change", summary, normalized_targets),
        summary=" ".join(summary.split()),
        target_paths=tuple(normalized_targets),
        constraints=("operator_review_required", "proposal_only", "no_auto_apply"),
        prohibited_actions=("shell_execution", "auto_patch", "commit", "push", "provider_call", "network_call"),
    )


def generate_implementation_proposal(index: PythonRepositoryIndex, request: BoundedChangeRequest) -> ImplementationProposal:
    affected = _match_targets(index, request.target_paths)
    if not affected:
        affected = tuple(record.path for record in index.files[: min(3, len(index.files))])
    tests = tuple(sorted({test for path in affected for test in index.test_map.get(path, ())}))
    return ImplementationProposal(
        proposal_id=stable_id("python-proposal", request.request_id, affected),
        request_id=request.request_id,
        affected_files=affected,
        rationale_summary=f"Prepare a bounded proposal for: {request.summary}",
        proposed_steps=(
            "inspect affected symbols and imports",
            "make the smallest reviewed source change",
            "update or add focused tests if needed",
            "ask operator before applying any patch",
        ),
        validation_plan=tests or ("operator_select_focused_tests", "py_compile_changed_files"),
        risk_notes=("proposal_not_applied", "operator_must_review_diff", "no_shell_execution_from_module"),
    )


def generate_patch_proposal(proposal: ImplementationProposal, *, replacement_hint: str = "operator-reviewed change") -> PatchProposal:
    lines = []
    for file in proposal.affected_files:
        lines.append(f"--- a/{file}")
        lines.append(f"+++ b/{file}")
        lines.append("@@ proposal only @@")
        lines.append(f"+# TODO(operator): {replacement_hint}")
    return PatchProposal(
        patch_id=stable_id("python-patch", proposal.proposal_id, replacement_hint),
        proposal_id=proposal.proposal_id,
        files=proposal.affected_files,
        diff_preview="\n".join(lines),
    )


def interpret_failure(output: str) -> FailureInterpretation:
    lower = output.lower()
    if "assert" in lower or "expected" in lower:
        klass = "assertion_failure"
        causes = ("logic_regression", "test_expectation_changed", "fixture_mismatch")
    elif "importerror" in lower or "modulenotfounderror" in lower:
        klass = "import_failure"
        causes = ("missing_dependency", "package_layout_issue", "test_path_issue")
    elif "syntaxerror" in lower:
        klass = "syntax_failure"
        causes = ("invalid_python_syntax", "incomplete_patch")
    else:
        klass = "unknown_failure"
        causes = ("need_full_traceback", "need_focused_reproduction")
    return FailureInterpretation(
        failure_id=stable_id("python-failure", output[:500]),
        failure_class=klass,
        likely_causes=causes,
        evidence_needed=("full_traceback", "changed_files", "focused_test_name"),
        bounded_next_steps=("inspect failure location", "map failing test to source", "prepare reviewed repair proposal"),
    )


def build_validation_plan(proposal: ImplementationProposal) -> ValidationPlan:
    focused = tuple(item for item in proposal.validation_plan if "test" in item.lower())
    return ValidationPlan(
        plan_id=stable_id("python-validation", proposal.proposal_id, proposal.validation_plan),
        commands_to_request_from_operator=("python -m py_compile changed_files", "pytest focused_tests -q"),
        focused_tests=focused or ("operator_selected_focused_tests",),
        static_checks=("path_guard_review", "secret_scan_staged_changes", "diff_review"),
        stop_conditions=("test_failure", "governance_regression", "operator_rejection"),
    )


def python_module_report(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    index = analyze_python_repository(root, max_files=120)
    request = build_change_request("Prepare a bounded Python proposal for operator review.", tuple(record.path for record in index.files[:1]), root=root)
    proposal = generate_implementation_proposal(index, request)
    patch = generate_patch_proposal(proposal)
    validation = build_validation_plan(proposal)
    return {
        "status": "PYTHON_CODING_MODULE_V1_READY_SHADOW_PROPOSE_PREPARE",
        "indexed_files": len(index.files),
        "packages": index.packages[:20],
        "sample_request": request,
        "sample_proposal": proposal,
        "sample_patch": patch,
        "validation_plan": validation,
        "safety": safety_metadata(),
    }


def _analyze_file(root: Path, path: Path, rel: str, text: str, size: int) -> PythonFileRecord:
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as exc:
        return PythonFileRecord(
            path=rel,
            package=_package_for(rel),
            bytes=size,
            symbols=(),
            imports=(),
            tests=(),
            side_effect_indicators=_side_effects(text),
            parse_error=f"SyntaxError:{exc.lineno}",
        )
    imports: list[PythonImport] = []
    symbols: list[PythonSymbol] = []
    tests: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(PythonImport(module=alias.name, imported_name=None, file=rel, line=node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            for alias in node.names:
                imports.append(PythonImport(module=module, imported_name=alias.name, file=rel, line=node.lineno, relative=node.level > 0))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol = PythonSymbol(
                name=node.name,
                kind="function",
                file=rel,
                line=node.lineno,
                decorators=tuple(_name(item) for item in node.decorator_list),
                calls=tuple(sorted(set(_calls(node)))),
                is_async=isinstance(node, ast.AsyncFunctionDef),
            )
            symbols.append(symbol)
            if node.name.startswith("test_") or rel.startswith("tests/"):
                tests.append(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols.append(
                PythonSymbol(
                    name=node.name,
                    kind="class",
                    file=rel,
                    line=node.lineno,
                    decorators=tuple(_name(item) for item in node.decorator_list),
                    calls=tuple(sorted(set(_calls(node)))),
                )
            )
    return PythonFileRecord(
        path=rel,
        package=_package_for(rel),
        bytes=size,
        symbols=tuple(symbols),
        imports=tuple(imports),
        tests=tuple(sorted(set(tests))),
        side_effect_indicators=_side_effects(text),
    )


def _safe_relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes approved root") from exc
    return rel.as_posix()


def _ignored(rel: str) -> bool:
    parts = rel.split("/")
    return any(part in DEFAULT_IGNORES for part in parts)


def _package_for(rel: str) -> str:
    path = Path(rel)
    if path.name == "__init__.py":
        return ".".join(path.parent.parts)
    return ".".join(path.with_suffix("").parts[:-1])


def _build_import_graph(records: list[PythonFileRecord]) -> dict[str, tuple[str, ...]]:
    return {
        record.path: tuple(sorted({item.module.lstrip(".") for item in record.imports if item.module}))
        for record in records
    }


def _build_symbol_index(records: list[PythonFileRecord]) -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for record in records:
        for symbol in record.symbols:
            index.setdefault(symbol.name, []).append(f"{record.path}:{symbol.line}:{symbol.kind}")
    return {key: tuple(sorted(value)) for key, value in sorted(index.items())}


def _build_test_map(records: list[PythonFileRecord]) -> dict[str, tuple[str, ...]]:
    tests = [record for record in records if record.path.startswith("tests/") or record.tests]
    source_records = [record for record in records if record not in tests]
    mapping: dict[str, tuple[str, ...]] = {}
    for source in source_records:
        stem = Path(source.path).stem.replace("test_", "")
        matches = tuple(sorted(test.path for test in tests if stem in test.path or any(sym.name in test.path for sym in source.symbols)))
        if matches:
            mapping[source.path] = matches
    return mapping


def _match_targets(index: PythonRepositoryIndex, targets: tuple[str, ...]) -> tuple[str, ...]:
    wanted = set(targets)
    return tuple(record.path for record in index.files if record.path in wanted or any(record.path.endswith(target) for target in wanted))


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _name(node.func)
    return node.__class__.__name__


def _calls(node: ast.AST) -> tuple[str, ...]:
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            names.append(_name(child.func))
    return tuple(names)


def _side_effects(text: str) -> tuple[str, ...]:
    markers = []
    checks = {
        "subprocess": r"\bsubprocess\b",
        "shell": r"\bos\.system\b|\bshell\s*=\s*True",
        "network": r"\brequests\.|\burllib\.|\bhttpx\.",
        "filesystem_write": r"\bwrite_text\b|\bopen\([^)]*['\"]w",
        "environment": r"\bos\.environ\b",
    }
    for name, pattern in checks.items():
        if re.search(pattern, text):
            markers.append(name)
    return tuple(markers)
