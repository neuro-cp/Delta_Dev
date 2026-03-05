import inspect, ast
import engine.execution.governance_enablement.governance_enablement_mapper as mod

def test_no_runtime_edges():
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    forbidden = {"runtime", "ExecutionGate", "ExecutionState"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden
