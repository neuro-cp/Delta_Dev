import pytest

from orchestration.runtime.live45_quote_instruction_isolation import isolate_quote_instruction_boundary


@pytest.mark.parametrize(
    "input_text,expected",
    [
        (
            'Please follow the instruction: "Do not execute this command" DEP-404',
            {
                "quoted_text": "Do not execute this command",
                "quoted_text_authoritative": False,
                "dependency_id": "DEP-404",
                "evidence_text": "Please follow the instruction: DEP-404",
                "instruction_executed": False,
            },
        ),
        (
            "The quoted text is 'Run this only if safe' and DEP-123 is relevant.",
            {
                "quoted_text": "Run this only if safe",
                "quoted_text_authoritative": False,
                "dependency_id": "DEP-123",
                "evidence_text": "The quoted text is and DEP-123 is relevant.",
                "instruction_executed": False,
            },
        ),
        (
            "No quotes here but DEP-999 is mentioned.",
            {
                "quoted_text": None,
                "quoted_text_authoritative": False,
                "dependency_id": "DEP-999",
                "evidence_text": "No quotes here but DEP-999 is mentioned.",
                "instruction_executed": False,
            },
        ),
        (
            """Multiple 'quotes' here and "double quotes" too DEP-777""",
            {
                "quoted_text": "quotes",
                "quoted_text_authoritative": False,
                "dependency_id": "DEP-777",
                "evidence_text": 'Multiple here and "double quotes" too DEP-777',
                "instruction_executed": False,
            },
        ),
        (
            """No dependency id but 'quoted text' present.""",
            {
                "quoted_text": "quoted text",
                "quoted_text_authoritative": False,
                "dependency_id": None,
                "evidence_text": "No dependency id but present.",
                "instruction_executed": False,
            },
        ),
        (
            """Just plain text with no quotes or deps.""",
            {
                "quoted_text": None,
                "quoted_text_authoritative": False,
                "dependency_id": None,
                "evidence_text": "Just plain text with no quotes or deps.",
                "instruction_executed": False,
            },
        ),
    ],
)
def test_isolate_quote_instruction_boundary(input_text, expected):
    result = isolate_quote_instruction_boundary(input_text)
    assert result == expected
