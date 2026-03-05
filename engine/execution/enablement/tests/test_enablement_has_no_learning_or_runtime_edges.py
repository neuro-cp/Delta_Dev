import inspect
import ast

import engine.execution.enablement.execution_enablement_controller as mod


def test_enablement_has_no_learning_or_runtime_edges():
    source = inspect.getsource(mod)
    tree = ast.parse(source)

    forbidden = {"runtime", "learning"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden
