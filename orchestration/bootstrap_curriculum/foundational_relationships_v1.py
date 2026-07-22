from __future__ import annotations

from orchestration.runtime.developmental_bootstrap import make_bootstrap_relationship

from .foundational_modules_v1 import DOMAINS


EXPLICIT_CROSS_DOMAIN_LINKS: tuple[tuple[str, str, str, str], ...] = (
    ("Evidence sufficiency and semantic support", "requires", "Claim evidence and support types", "Evidence sufficiency requires claim versus evidence."),
    ("Failure diagnosis from criteria", "requires", "Counterexamples comparison and contrast", "Failure diagnosis requires comparison."),
    ("Failure diagnosis from criteria", "requires", "Success criteria and stopping conditions", "Failure diagnosis requires success criteria."),
    ("Revision after failure", "requires", "Feedback interpretation and progress monitoring", "Revision after failure requires feedback interpretation and progress monitoring."),
    ("Booleans and conditions", "requires", "Logical operators", "Python conditions require booleans and logical operators."),
    ("Loops over sequences", "requires", "Sequence ordering and state machines", "Python loops require sequence and state."),
    ("JSON serialization", "requires", "Records fields and schemas", "JSON requires records."),
    ("JSON serialization", "requires", "Serialization and parsing", "JSON requires serialization."),
    ("JSON serialization", "requires", "Hierarchical data", "JSON requires hierarchical data."),
    ("CSV tabular parsing", "requires", "Records fields and schemas", "CSV requires records."),
    ("CSV tabular parsing", "requires", "Serialization and parsing", "CSV requires parsing."),
    ("CSV tabular parsing", "requires", "Tabular data", "CSV requires tabular data."),
    ("Schema validation in Python", "requires", "Missing values and extra values", "Schema validation requires missing and extra value handling."),
    ("Schema validation in Python", "requires", "Validation rules", "Schema validation requires validation rules."),
    ("Sequence ordering and state machines", "requires", "Queued active blocked and completed states", "State machines require states."),
    ("Terminal states and integrity stops", "requires", "Booleans and conditions", "Terminal states require conditional tests."),
    ("Comparison and falsification", "requires", "Hypotheses variables and controls", "Falsification requires hypotheses."),
    ("Comparison and falsification", "requires", "Evidence sufficiency and semantic support", "Falsification requires evidence."),
    ("Comparison and falsification", "requires", "Counterexamples comparison and contrast", "Falsification uses counterexamples."),
    ("Evidence grounded question answering", "requires", "Source provenance and source artifacts", "Evidence-grounded answering requires source provenance."),
    ("Evidence grounded question answering", "requires", "Summarization and scoped explanation", "Evidence-grounded answering requires scoped explanation."),
    ("Goal decomposition and prerequisite discovery", "transfers_to", "Task decomposition and dependencies", "Goal decomposition transfers to planning decomposition."),
    ("Runtime transition checkpoints", "requires", "Versioning and immutable records", "Checkpoints require immutable records."),
    ("Analytical claims from observations", "requires", "Claim evidence and support types", "Analytical claims require claim and evidence distinctions."),
    ("Debugging with evidence", "transfers_to", "Failure diagnosis from criteria", "Debugging transfers failure diagnosis to code."),
    ("Data and structure foundations", "relates_to", "Python foundations", "domain-summary-placeholder"),
)


def _by_title(modules: tuple[dict, ...]) -> dict[str, dict]:
    return {module["title"]: module for module in modules}


def _domain_groups(modules: tuple[dict, ...]) -> dict[str, tuple[dict, ...]]:
    return {
        domain: tuple(module for module in modules if module["domain"] == domain)
        for domain in DOMAINS
    }


def _relationship(source: dict, relationship_type: str, target: dict, rationale: str) -> dict:
    return make_bootstrap_relationship(
        source_module_id=source["module_id"],
        target_module_id=target["module_id"],
        relationship_type=relationship_type,
        rationale=rationale,
    )


def build_foundational_relationships_v1(modules: tuple[dict, ...]) -> tuple[dict, ...]:
    relationships: list[dict] = []
    groups = _domain_groups(modules)
    for domain, domain_modules in groups.items():
        for index, module in enumerate(domain_modules):
            if index > 0:
                prior = domain_modules[index - 1]
                relationships.append(_relationship(module, "requires", prior, f"{module['title']} builds on {prior['title']}."))
                relationships.append(_relationship(prior, "enables", module, f"{prior['title']} prepares {module['title']}."))
            related = domain_modules[(index + 2) % len(domain_modules)]
            if related["module_id"] != module["module_id"]:
                relationships.append(_relationship(module, "relates_to", related, f"{module['title']} is related to {related['title']} within {domain}."))
    titles = _by_title(modules)
    for source_title, relationship_type, target_title, rationale in EXPLICIT_CROSS_DOMAIN_LINKS:
        if source_title in titles and target_title in titles:
            relationships.append(_relationship(titles[source_title], relationship_type, titles[target_title], rationale))
    semantic: dict[tuple[str, str, str], dict] = {}
    for relationship in relationships:
        key = (relationship["source_module_id"], relationship["relationship_type"], relationship["target_module_id"])
        semantic.setdefault(key, relationship)
    return tuple(sorted(semantic.values(), key=lambda item: item["relationship_id"]))
