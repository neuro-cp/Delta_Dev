import inspect, ast
import engine.execution.proposal_governance.proposal_governance_evaluator as mod

def test_no_runtime_edges():
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    forbidden = {"runtime", "ExecutionGate", "ExecutionState"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden
