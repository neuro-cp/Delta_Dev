import inspect, ast
import engine.execution.proposals.execution_proposal_evaluator as mod

def test_proposals_have_no_runtime_or_gate_edges():
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    forbidden = {"runtime", "ExecutionGate", "ExecutionState"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert node.id not in forbidden
