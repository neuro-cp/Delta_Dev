from __future__ import annotations

from memory.context.context_policy import ContextPolicy


def main() -> None:
    print("=== CONTEXT POLICY TRACE ELIGIBILITY TEST ===")

    tests = [
        # gain, duration, expected
        ("below gain threshold", 0.1, 2.0, False),
        ("above gain, too short", 0.3, 0.5, False),
        ("at gain, at duration", ContextPolicy.TRACE_GAIN_THRESHOLD,
         ContextPolicy.TRACE_MIN_DURATION, True),
        ("above gain, above duration", 0.5, 2.0, True),
        ("large gain, instant spike", 1.0, 0.1, False),
    ]

    for label, gain, duration, expected in tests:
        allowed = ContextPolicy.should_create_trace(
            gain=gain,
            duration=duration,
            domain="global",
        )

        status = "PASS" if allowed == expected else "FAIL"
        print(
            f"[{status}] {label:28s} | "
            f"gain={gain: .3f} | "
            f"duration={duration: .2f}s | "
            f"eligible={allowed}"
        )

    print("\nActive policy:")
    print(ContextPolicy.describe())

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
