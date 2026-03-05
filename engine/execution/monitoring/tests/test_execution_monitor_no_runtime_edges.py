import inspect, ast
import engine.execution.monitoring.execution_monitor as mod

def test_no_runtime_edges():
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    forbidden = {"runtime"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden
