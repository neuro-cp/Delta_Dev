from __future__ import annotations

import ast
import inspect

import memory.semantic_assembly_hypotheses as sah


FORBIDDEN_IMPORT_ROOTS = {
    "engine",
    "runtime",
    "routing",
    "salience",
    "value",
    "urgency",
    "learning",
    "decision",
    "replay",
    "cognition",
}


def _import_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                roots.add(name.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])

    return roots


def test_semantic_assembly_hypotheses_has_no_forbidden_imports() -> None:
    source = inspect.getsource(sah)
    roots = _import_roots(source)

    assert roots.isdisjoint(
        FORBIDDEN_IMPORT_ROOTS
    ), f"Forbidden imports detected: {roots & FORBIDDEN_IMPORT_ROOTS}"
