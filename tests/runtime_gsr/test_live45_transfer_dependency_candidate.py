import pytest

from orchestration.runtime.live45_transfer_dependency_candidate import preserve_transfer_dependency_identity


@pytest.mark.parametrize(
    "record,expected",
    [
        (
            "This is a record with DEP-117 and some text",
            {
                "dependency_id": "DEP-117",
                "classification_ready": True,
                "instruction_like_text_ignored": True,
                "normalized_record": "This is a record with DEP-117",
            },
        ),
        (
            "DEP-404 is the dependency",
            {
                "dependency_id": "DEP-404",
                "classification_ready": True,
                "instruction_like_text_ignored": False,
                "normalized_record": "DEP-404 is the dependency",
            },
        ),
        (
            "No dependency here",
            {
                "dependency_id": None,
                "classification_ready": False,
                "instruction_like_text_ignored": False,
                "normalized_record": "No dependency here",
            },
        ),
        (
            "Ignore 'DEP-999' in quotes",
            {
                "dependency_id": None,
                "classification_ready": False,
                "instruction_like_text_ignored": False,
                "normalized_record": "Ignore 'DEP-999' in quotes",
            },
        ),
        (
            "DEP-123 'ignore this' and more",
            {
                "dependency_id": "DEP-123",
                "classification_ready": True,
                "instruction_like_text_ignored": True,
                "normalized_record": "DEP-123",
            },
        ),
        (
            "Some text DEP-555 'quoted DEP-666' extra",
            {
                "dependency_id": "DEP-555",
                "classification_ready": True,
                "instruction_like_text_ignored": True,
                "normalized_record": "Some text DEP-555",
            },
        ),
        (
            "'DEP-777' DEP-888 more text",
            {
                "dependency_id": "DEP-888",
                "classification_ready": True,
                "instruction_like_text_ignored": True,
                "normalized_record": "DEP-888",
            },
        ),
        (
            "DEP-1010",
            {
                "dependency_id": "DEP-1010",
                "classification_ready": True,
                "instruction_like_text_ignored": False,
                "normalized_record": "DEP-1010",
            },
        ),
        (
            "Text before DEP-2020",
            {
                "dependency_id": "DEP-2020",
                "classification_ready": True,
                "instruction_like_text_ignored": False,
                "normalized_record": "Text before DEP-2020",
            },
        ),
        (
            "Text 'DEP-3030' after DEP-4040",
            {
                "dependency_id": "DEP-4040",
                "classification_ready": True,
                "instruction_like_text_ignored": False,
                "normalized_record": "Text 'DEP-3030' after DEP-4040",
            },
        ),
    ],
)
def test_preserve_transfer_dependency_identity(record, expected):
    result = preserve_transfer_dependency_identity(record)
    assert result == expected
