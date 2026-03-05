import inspect
import ast

import engine.execution.governance.operator_execution_authorization as auth


def test_governance_has_no_runtime_edges():
    source = inspect.getsource(auth)
    tree = ast.parse(source)

    forbidden_names = {
        "runtime",
        "BrainRuntime",
        "ExecutionGate",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                assert name.name not in forbidden_names

        if isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_names

        if isinstance(node, ast.Name):
            assert node.id not in forbidden_names
