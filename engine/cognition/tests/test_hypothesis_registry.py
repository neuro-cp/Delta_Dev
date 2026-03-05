from __future__ import annotations

import json

import pytest

from engine.cognition.hypothesis_registry import HypothesisRegistry


# ============================================================
# Test: Hypothesis creation & defaults
# ============================================================

def test_hypothesis_creation_defaults():
    registry = HypothesisRegistry()

    h = registry.create(
        hypothesis_id="H-001",
        created_step=10,
    )

    assert h.hypothesis_id == "H-001"
    assert h.created_step == 10

    # inert defaults
    assert h.activation == 0.0
    assert h.support == 0.0
    assert h.age == 0
    assert h.active is True

    assert len(registry) == 1


# ============================================================
# Test: Duplicate ID protection
# ============================================================

def test_duplicate_hypothesis_id_raises():
    registry = HypothesisRegistry()

    registry.create(
        hypothesis_id="H-dup",
        created_step=0,
    )

    with pytest.raises(ValueError):
        registry.create(
            hypothesis_id="H-dup",
            created_step=1,
        )


# ============================================================
# Test: Explicit lifecycle control
# ============================================================

def test_hypothesis_removal():
    registry = HypothesisRegistry()

    registry.create(
        hypothesis_id="H-remove",
        created_step=5,
    )

    assert registry.get("H-remove") is not None

    registry.remove("H-remove")

    assert registry.get("H-remove") is None
    assert len(registry) == 0


# ============================================================
# Test: Explicit age advancement only
# ============================================================

def test_tick_advances_age_only_when_called():
    registry = HypothesisRegistry()

    h1 = registry.create(hypothesis_id="H-A", created_step=0)
    h2 = registry.create(hypothesis_id="H-B", created_step=0)

    assert h1.age == 0
    assert h2.age == 0

    registry.tick()

    assert h1.age == 1
    assert h2.age == 1

    registry.tick()
    registry.tick()

    assert h1.age == 3
    assert h2.age == 3


# ============================================================
# Test: Isolation / inertness guarantee
# ============================================================

def test_registry_is_inert_without_calls():
    registry = HypothesisRegistry()

    registry.create(hypothesis_id="H-iso", created_step=42)
    h = registry.get("H-iso")

    for _ in range(100):
        pass

    assert h.activation == 0.0
    assert h.support == 0.0
    assert h.age == 0
    assert h.active is True


# ============================================================
# Test: Audit dump stability
# ============================================================

def test_dump_state_is_json_serializable_and_stable():
    registry = HypothesisRegistry()

    registry.create(hypothesis_id="H-1", created_step=1)
    registry.create(hypothesis_id="H-2", created_step=2)

    dump = registry.dump_state()

    assert set(dump.keys()) == {"H-1", "H-2"}

    for record in dump.values():
        assert "hypothesis_id" in record
        assert "created_step" in record
        assert "activation" in record
        assert "support" in record
        assert "age" in record
        assert "active" in record

    json.dumps(dump)
