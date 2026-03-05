from __future__ import annotations

from engine.vta_value.value_signal import ValueSignal


def main() -> None:
    """
    TEST: ValueSignal dynamics are bounded, decaying, and time-continuous.

    Invariants:
    - Value decays toward zero
    - Decay rate respects decay_tau
    - Value never goes negative
    - Value never explodes
    """

    sig = ValueSignal(
        decay_tau=6.0,   # slower than salience, faster than memory
    )

    # --------------------------------------------------
    # 1. Initial state
    # --------------------------------------------------
    assert sig.get() == 0.0, "Initial value is not zero"

    # --------------------------------------------------
    # 2. Set a value
    # --------------------------------------------------
    sig.set(1.0)
    v0 = sig.get()

    assert v0 == 1.0, "ValueSignal.set() failed"

    # --------------------------------------------------
    # 3. Single-step decay
    # --------------------------------------------------
    sig.step(dt=1.0)
    v1 = sig.get()

    assert 0.0 < v1 < v0, "Value did not decay after step"

    # --------------------------------------------------
    # 4. Multi-step decay is monotonic
    # --------------------------------------------------
    prev = v1
    for _ in range(5):
        sig.step(dt=1.0)
        cur = sig.get()
        assert 0.0 <= cur <= prev, "Value decay is not monotonic"
        prev = cur

    # --------------------------------------------------
    # 5. Long-run decay approaches zero
    # --------------------------------------------------
    for _ in range(50):
        sig.step(dt=1.0)

    final = sig.get()
    assert final == 0.0 or final < 1e-4, "Value failed to decay to zero"

    # --------------------------------------------------
    # 6. Value never goes negative
    # --------------------------------------------------
    sig.set(0.5)
    for _ in range(20):
        sig.step(dt=1.0)
        assert sig.get() >= 0.0, "Value went negative"

    # --------------------------------------------------
    # 7. Re-setting value works cleanly
    # --------------------------------------------------
    sig.set(0.8)
    assert sig.get() == 0.8, "Value reset failed"


if __name__ == "__main__":
    main()
