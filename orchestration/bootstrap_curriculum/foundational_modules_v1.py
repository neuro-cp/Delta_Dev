from __future__ import annotations

from collections.abc import Iterable

from orchestration.runtime.developmental_bootstrap import bootstrap_digest, make_bootstrap_module


CURRICULUM_TITLE = "Governed Foundational Bootstrap Curriculum"
CURRICULUM_VERSION = 1
CURRICULUM_SEED = "governed-foundational-bootstrap-curriculum-v1"

DOMAINS: tuple[str, ...] = (
    "learning_and_reasoning",
    "evidence_and_research",
    "planning_and_control",
    "communication_and_language",
    "mathematical_foundations",
    "python_foundations",
    "data_and_structure",
    "scientific_and_analytical_reasoning",
)

DOMAIN_MODULE_TITLES: dict[str, tuple[str, ...]] = {
    "learning_and_reasoning": (
        "Goal decomposition and prerequisite discovery",
        "Success criteria and stopping conditions",
        "Definitions procedures and examples",
        "Counterexamples comparison and contrast",
        "Claim evidence and support types",
        "Uncertainty and scope limits",
        "Failure diagnosis from criteria",
        "Feedback interpretation and progress monitoring",
        "Revision after failure",
        "Transfer across related tasks",
        "Direct and indirect conceptual support",
        "Learning boundary summaries",
    ),
    "evidence_and_research": (
        "Source provenance and source artifacts",
        "Immutable evidence and artifact digests",
        "Excerpt mapping and accepted excerpts",
        "Rejected excerpts and missing evidence",
        "Evidence sufficiency and semantic support",
        "Evidence conflict and uncertainty",
        "Advisory provider output",
        "Authoritative evidence",
        "Retrieval success versus support",
        "Digest only evidence limitations",
        "Evaluator isolation and hidden content",
        "Learner visible evidence bundles",
    ),
    "planning_and_control": (
        "Task decomposition and dependencies",
        "Queued active blocked and completed states",
        "Sequence ordering and state machines",
        "Terminal states and integrity stops",
        "Budgets and bounded work",
        "Exact once execution",
        "Duplicate suppression",
        "Retry and revision control",
        "Operator authority boundaries",
        "Runtime transition checkpoints",
        "Goal disposition taxonomy",
    ),
    "communication_and_language": (
        "Structured instructions and explicit constraints",
        "Implicit dependencies and ambiguity detection",
        "Summarization and scoped explanation",
        "Procedural explanation and argument structure",
        "Contextual continuity and topic switching",
        "Evidence grounded question answering",
        "Instruction hierarchy",
        "Audience calibrated language",
    ),
    "mathematical_foundations": (
        "Arithmetic and estimation",
        "Fractions ratios and percentages",
        "Comparison and ordering",
        "Variables and basic algebra",
        "Equations and units",
        "Logical operators",
        "Sets and membership",
        "Simple probability",
        "Tables and graphs",
        "Quantitative reasonableness checks",
    ),
    "python_foundations": (
        "Values types strings and numbers",
        "Booleans and conditions",
        "Lists tuples dictionaries and sets",
        "Loops over sequences",
        "Functions parameters and return values",
        "Exceptions and imports",
        "Paths and file reading",
        "File writing and resource boundaries",
        "JSON serialization",
        "CSV tabular parsing",
        "Assertions and tests",
        "Debugging with evidence",
        "State representation in Python",
        "Schema validation in Python",
    ),
    "data_and_structure": (
        "Records fields and schemas",
        "Missing values and extra values",
        "Serialization and parsing",
        "Validation rules",
        "Tabular data",
        "Hierarchical data",
        "Identifiers and references",
        "Graphs and parent child relationships",
        "Versioning and immutable records",
    ),
    "scientific_and_analytical_reasoning": (
        "Observation and measurement",
        "Hypotheses variables and controls",
        "Comparison and falsification",
        "Replication and experimental error",
        "Correlation and causation",
        "Confidence and limitations",
        "Evidence revision in analysis",
        "Analytical claims from observations",
    ),
}

SOURCE_TYPES_BY_DOMAIN: dict[str, str] = {
    "python_foundations": "python_official_documentation",
    "mathematical_foundations": "established_mathematical_definitions",
    "scientific_and_analytical_reasoning": "standard_scientific_method_reference",
}


def _source_binding(domain: str, title: str) -> dict[str, str]:
    source_type = SOURCE_TYPES_BY_DOMAIN.get(domain, "operator_authored_framework")
    locator = {
        "python_official_documentation": "https://docs.python.org/3/",
        "established_mathematical_definitions": "operator://standard-mathematics-foundations",
        "standard_scientific_method_reference": "operator://standard-scientific-method-foundations",
        "operator_authored_framework": "operator://delta-governed-bootstrap-framework",
    }[source_type]
    source_id = f"{source_type}:{domain}:{title}".lower().replace(" ", "-")
    return {
        "source_id": source_id,
        "source_type": source_type,
        "locator": locator,
        "artifact_digest": bootstrap_digest((source_type, locator, domain, title)),
        "retrieved_in_phase": "not_retrieved_bootstrap_c",
    }


def _components(title: str) -> tuple[str, ...]:
    words = tuple(word for word in title.lower().replace("and", " ").split() if word)
    return tuple(dict.fromkeys((*words[:5], "definition", "boundary")))


def _procedure(title: str) -> tuple[str, ...]:
    return (
        f"Identify the relevant part of {title.lower()}.",
        "State the evidence or rule being used.",
        "Apply the concept within its stated scope limit.",
    )


def _module(domain: str, title: str, prerequisites: Iterable[str]) -> dict:
    return make_bootstrap_module(
        title=title,
        domain=domain,
        definition=f"{title} is an operator-authored bootstrap concept for the {domain.replace('_', ' ')} domain.",
        prerequisites=tuple(prerequisites),
        key_components=_components(title),
        procedure=_procedure(title),
        worked_examples=(
            {
                "prompt": f"Use {title} in a bounded learning task.",
                "response": f"Apply {title} only as unvalidated bootstrap scaffolding with retained provenance.",
            },
        ),
        counterexamples=(
            {
                "prompt": f"Treat {title} as demonstrated DELTA competence.",
                "response": "Reject the claim because operator-installed curriculum is not behavioral validation.",
            },
        ),
        failure_modes=(f"Using {title} outside its scope without evidence.",),
        verification_methods=(f"Check that a later evaluator can distinguish correct and incorrect use of {title}.",),
        scope_limits=("This module is educational scaffolding and makes no competence, authority, or trusted-memory claim.",),
        source_bindings=(_source_binding(domain, title),),
    )


def build_foundational_modules_v1() -> tuple[dict, ...]:
    modules: list[dict] = []
    prior_by_domain: dict[str, str] = {}
    for domain in DOMAINS:
        for title in DOMAIN_MODULE_TITLES[domain]:
            prerequisites = (prior_by_domain[domain],) if domain in prior_by_domain else ()
            module = _module(domain, title, prerequisites)
            modules.append(module)
            prior_by_domain[domain] = module["module_id"]
    return tuple(modules)
