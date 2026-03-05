from __future__ import annotations

from types import SimpleNamespace

from engine.salience.salience_policy import SaliencePolicy


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def fake_pop(
    *,
    assembly_id: str,
    activity: float,
    baseline: float = 0.0,
    firing_rate: float = 0.0,
    sign: float = 1.0,
    role: str | None = None,
) -> SimpleNamespace:
    """
    Minimal stand-in for PopulationModel.
    Only fields used by SaliencePolicy are included.
    """
    return SimpleNamespace(
        assembly_id=assembly_id,
        activity=activity,
        baseline=baseline,
        firing_rate=firing_rate,
        sign=sign,
        semantic_role=role,
    )


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

def test_no_activity_no_salience() -> None:
    """
    Flat physiology should produce no proposals.
    """
    pop = fake_pop(
        assembly_id="A",
        activity=0.0,
        baseline=0.0,
        firing_rate=0.0,
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert proposals == {}


def test_activity_deviation_produces_salience() -> None:
    """
    Activity deviation above threshold should propose salience.
    """
    pop = fake_pop(
        assembly_id="A",
        activity=0.05,
        baseline=0.0,
        firing_rate=0.0,
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert "A" in proposals
    assert 0.0 < proposals["A"] <= SaliencePolicy.MAX_DELTA


def test_firing_rate_contributes() -> None:
    """
    Elevated firing rate should contribute to salience.
    """
    pop = fake_pop(
        assembly_id="A",
        activity=0.0,
        baseline=0.0,
        firing_rate=0.2,
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert "A" in proposals
    assert proposals["A"] > 0.0


def test_inhibitory_scaled_down() -> None:
    """
    Inhibitory populations must have reduced salience.
    """
    exc = fake_pop(
        assembly_id="E",
        activity=0.06,
        baseline=0.0,
        sign=1.0,
    )
    inh = fake_pop(
        assembly_id="I",
        activity=0.06,
        baseline=0.0,
        sign=-1.0,
    )

    props = SaliencePolicy.propose_updates([exc, inh])

    assert "E" in props
    assert "I" in props
    assert props["I"] < props["E"]


def test_interneuron_scaled_down() -> None:
    """
    Interneurons must be conservative salience sources.
    """
    pop = fake_pop(
        assembly_id="INT",
        activity=0.06,
        baseline=0.0,
        role="interneuron",
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert "INT" in proposals
    assert proposals["INT"] < SaliencePolicy.MAX_DELTA


def test_sensory_scaled_up_but_capped() -> None:
    """
    Sensory populations may be amplified, but never exceed MAX_DELTA.
    """
    pop = fake_pop(
        assembly_id="S",
        activity=0.2,
        baseline=0.0,
        role="sensory_input",
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert "S" in proposals
    assert proposals["S"] <= SaliencePolicy.MAX_DELTA


def test_oversized_proposals_are_capped() -> None:
    """
    Policy must cap proposals before approval.
    """
    pop = fake_pop(
        assembly_id="A",
        activity=10.0,
        baseline=0.0,
        firing_rate=10.0,
    )

    proposals = SaliencePolicy.propose_updates([pop])
    assert proposals["A"] == SaliencePolicy.MAX_DELTA


def test_allow_rules_still_enforced() -> None:
    """
    Proposal output must always pass allow_update.
    """
    pop = fake_pop(
        assembly_id="A",
        activity=0.05,
        baseline=0.0,
    )

    proposals = SaliencePolicy.propose_updates([pop])
    delta = proposals["A"]

    assert SaliencePolicy.allow_update("A", delta) is True
