from pathlib import Path

from orchestration.runtime.delta_1_0_python_module import (
    analyze_python_repository,
    build_change_request,
    build_validation_plan,
    generate_implementation_proposal,
    generate_patch_proposal,
    interpret_failure,
)


def _fixture_repo(root: Path) -> None:
    pkg = root / "pkg"
    tests = root / "tests"
    pkg.mkdir()
    tests.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "calc.py").write_text(
        "import math\n\n"
        "def add(a, b):\n"
        "    return a + b\n\n"
        "class Calculator:\n"
        "    def run(self):\n"
        "        return add(1, 2)\n",
        encoding="utf-8",
    )
    (tests / "test_calc.py").write_text(
        "from pkg.calc import add\n\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )


def test_python_repository_index_extracts_symbols_imports_and_tests(tmp_path):
    _fixture_repo(tmp_path)
    index = analyze_python_repository(tmp_path)
    assert len(index.files) == 3
    assert "add" in index.symbol_index
    assert any("math" in imports for imports in index.import_graph.values())
    assert any(value for value in index.test_map.values())


def test_path_guard_rejects_escape(tmp_path):
    _fixture_repo(tmp_path)
    try:
        build_change_request("bad", ("../secret.py",), root=tmp_path)
    except ValueError as exc:
        assert "relative" in str(exc)
    else:
        raise AssertionError("expected path escape rejection")


def test_proposal_and_patch_are_inert(tmp_path):
    _fixture_repo(tmp_path)
    index = analyze_python_repository(tmp_path)
    request = build_change_request("change add", ("pkg/calc.py",), root=tmp_path)
    proposal = generate_implementation_proposal(index, request)
    patch = generate_patch_proposal(proposal)
    validation = build_validation_plan(proposal)
    assert proposal.authority == "proposal_only"
    assert patch.applies_automatically is False
    assert validation.executes_now is False


def test_failure_interpreter_classifies_import_failures():
    failure = interpret_failure("ModuleNotFoundError: No module named 'pkg'")
    assert failure.failure_class == "import_failure"
    assert "missing_dependency" in failure.likely_causes
