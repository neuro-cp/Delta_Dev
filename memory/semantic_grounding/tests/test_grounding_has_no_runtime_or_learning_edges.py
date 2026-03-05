from __future__ import annotations

import inspect
import ast

import memory.semantic_grounding as sg


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
}


def _extract_import_roots(source: str) -> set[str]:
    """
    Parse Python source and extract top-level import roots.
    """
    tree = ast.parse(source)
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                roots.add(name.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                roots.add(node.module.split(".")[0])

    return roots


def test_grounding_module_has_no_forbidden_imports() -> None:
    source = inspect.getsource(sg)
    import_roots = _extract_import_roots(source)

    assert import_roots.isdisjoint(
        FORBIDDEN_IMPORT_ROOTS
    ), f"Forbidden imports detected: {import_roots & FORBIDDEN_IMPORT_ROOTS}"
