import inspect
import memory.proposal_evaluation.evaluation_engine as eng


def test_no_authority_imports() -> None:
    source = inspect.getsource(eng)

    forbidden = [
        "runtime",
        "decision",
        "salience",
        "routing",
        "value",
        "learning",
        "replay",
    ]

    for token in forbidden:
        assert token not in source
