import re


_DEPENDENCY_PATTERN = re.compile(r"DEP-\d+")
_QUOTED_PATTERN = re.compile(r"'[^']*'|\"[^\"]*\"")


def _quoted_spans(record: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _QUOTED_PATTERN.finditer(record)]


def _inside_spans(index: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in spans)


def _prefix_without_quoted_noise(prefix: str) -> str:
    cleaned = _QUOTED_PATTERN.sub("", prefix)
    return " ".join(cleaned.split())


def _suffix_is_context(suffix: str) -> bool:
    normalized = " ".join(suffix.split()).lower()
    return normalized in {"", "is the dependency"}


def preserve_transfer_dependency_identity(record: str) -> dict:
    quoted = _quoted_spans(record)
    dependency_match = next(
        (match for match in _DEPENDENCY_PATTERN.finditer(record) if not _inside_spans(match.start(), quoted)),
        None,
    )
    if dependency_match is None:
        return {
            "dependency_id": None,
            "classification_ready": False,
            "instruction_like_text_ignored": False,
            "normalized_record": record,
        }

    dependency_id = dependency_match.group()
    prefix = record[: dependency_match.start()]
    suffix = record[dependency_match.end() :]
    classification_ready = True
    instruction_like_text_ignored = not _suffix_is_context(suffix)

    if instruction_like_text_ignored:
        prefix_context = _prefix_without_quoted_noise(prefix)
        normalized_record = f"{prefix_context} {dependency_id}".strip()
    else:
        normalized_record = record

    return {
        "dependency_id": dependency_id,
        "classification_ready": classification_ready,
        "instruction_like_text_ignored": instruction_like_text_ignored,
        "normalized_record": normalized_record,
    }
