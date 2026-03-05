from engine.decision_bias import DecisionBias


# ============================================================
# Test 1 — Baseline decay still works
# ============================================================

def test_decay_only():
    bias = DecisionBias(decay_tau=1.0, max_bias=0.3)

    bias.apply_decision(
        winner="D1",
        channels=["D1", "D2"],
        strength=1.0,
        step=0,
    )

    v0 = bias.get("D1")
    bias.step(0.1)
    v1 = bias.get("D1")

    assert v1 < v0
    assert v1 > 0.0


# ============================================================
# Test 2 — External modifier applies once and clears
# ============================================================

def test_external_modifier_one_shot():
    bias = DecisionBias(decay_tau=10.0, max_bias=0.3)

    bias.apply_decision(
        winner="D1",
        channels=["D1", "D2"],
        strength=1.0,
        step=0,
    )

    def amplify(bias_map):
        bias_map["D1"] *= 2.0
        return bias_map

    bias.apply_external(amplify)

    bias.step(0.1)
    boosted = bias.get("D1")

    bias.step(0.1)
    after = bias.get("D1")

    assert boosted > after


# ============================================================
# Test 3 — Hard clamp cannot be violated
# ============================================================

def test_external_modifier_clamped():
    bias = DecisionBias(decay_tau=10.0, max_bias=0.3)

    bias.apply_decision(
        winner="D1",
        channels=["D1", "D2"],
        strength=1.0,
        step=0,
    )

    def evil_modifier(bias_map):
        bias_map["D1"] = 999.0
        bias_map["D2"] = -999.0
        return bias_map

    bias.apply_external(evil_modifier)
    bias.step(0.1)

    assert bias.get("D1") <= 0.3
    assert bias.get("D2") >= -0.3


# ============================================================
# Test 4 — Near-zero cleanup
# ============================================================

def test_zero_cleanup():
    bias = DecisionBias(decay_tau=1.0)

    bias._bias["D1"] = 1e-8
    bias.step(0.1)

    assert "D1" not in bias.dump()
