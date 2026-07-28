"""Deterministic, dependency-free case generation for routing closure tests."""

from __future__ import annotations

from itertools import combinations


DIMENSIONS = {
    "semantic": ("goal_question", "pause_question", "provider_question", "adoption_question", "side_thread_question"),
    "order": ("control_first", "question_first"),
    "conjunction": ("also", "and", "but"),
    "casing": ("normal", "lower"),
    "punctuation": ("normal", "run_on"),
    "formality": ("formal", "casual", "plain"),
    "approval": ("yes", "okay", "approve", "go_ahead"),
    "denial": ("no", "not_yet", "leave_it", "dont"),
    "reference": ("explicit", "pronoun", "omitted"),
    "temporal": ("now", "later", "after_restart"),
    "constraint": ("none", "only", "except", "do_not"),
    "noise": ("clean", "minor_typo", "speech_like"),
}


def generate_pairwise_assignments() -> tuple[dict[str, str], ...]:
    """Greedily cover every pair of values once with deterministic tie breaks."""
    names = tuple(DIMENSIONS)
    requested = {
        (left, left_value, right, right_value)
        for left, right in combinations(names, 2)
        for left_value in DIMENSIONS[left]
        for right_value in DIMENSIONS[right]
    }
    # One valid, explicit row for every uncovered value pair. This is larger
    # than an IPOG-style minimum but easy to audit and package-free.
    default = {name: values[0] for name, values in DIMENSIONS.items()}
    selected: list[dict[str, str]] = []
    covered: set[tuple[str, str, str, str]] = set()
    for left, right in combinations(names, 2):
        for left_value in DIMENSIONS[left]:
            for right_value in DIMENSIONS[right]:
                pair = (left, left_value, right, right_value)
                if pair in covered:
                    continue
                row = {**default, left: left_value, right: right_value}
                selected.append(row)
                covered |= {
                    (a, row[a], b, row[b])
                    for a, b in combinations(names, 2)
                }
    assert requested <= covered
    return tuple(selected)


def pairwise_coverage_report(assignments: tuple[dict[str, str], ...]) -> dict[str, object]:
    names = tuple(DIMENSIONS)
    requested = {
        (left, left_value, right, right_value)
        for left, right in combinations(names, 2)
        for left_value in DIMENSIONS[left]
        for right_value in DIMENSIONS[right]
    }
    covered = {
        (left, assignment[left], right, assignment[right])
        for assignment in assignments
        for left, right in combinations(names, 2)
    }
    return {
        "requested_dimension_pairs": len(requested),
        "covered_dimension_pairs": len(requested & covered),
        "uncovered_pairs": sorted(requested - covered),
        "invalid_or_excluded_pairs": [],
    }


def render_pairwise_prompt(case: dict[str, str]) -> tuple[str, str | None]:
    question = "What color is the sky"
    semantic = case["semantic"]
    setup = None
    if semantic == "goal_question":
        control = "Your new goal is to study engines"
    elif semantic == "pause_question":
        control, setup = "Pause the goal", "goal"
    elif semantic == "provider_question":
        control, setup = "Approve one provider call", "provider_authority"
    elif semantic == "adoption_question":
        control, setup = "Yes, adopt it", "capability_adoption_and_restart"
    else:
        control, setup = "Yes, prioritize topic switches", "directional_question"
    glue = case["conjunction"]
    parts = (control, question) if case["order"] == "control_first" else (question, control)
    if case["punctuation"] == "normal":
        prompt = f"{parts[0].rstrip('.?')}. {glue.capitalize()} {parts[1].rstrip('.?')}?"
    else:
        prompt = f"{parts[0].rstrip('.?')} {glue} {parts[1].rstrip('.?')}?"
    if case["casing"] == "lower":
        prompt = prompt.lower()
    return prompt, setup
