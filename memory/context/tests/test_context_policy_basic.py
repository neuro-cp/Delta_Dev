from __future__ import annotations

from memory.context.context_policy import ContextPolicy


def main() -> None:
    print("=== CONTEXT POLICY BASIC TEST ===")

    tests = [
        ("zero delta", 0.0, False),
        ("tiny noise", 1e-6, False),
        ("sub-threshold", 5e-4, False),
        ("at threshold", ContextPolicy.MIN_EFFECTIVE_DELTA, True),
        ("above threshold", 1e-2, True),
        ("large signal", 0.5, True),
        ("negative noise", -5e-4, False),
        ("negative signal", -0.1, True),
    ]

    for label, delta, expected in tests:
        allowed = ContextPolicy.allow_update(
            assembly_id="pfc:L2:0",
            domain="global",
            delta=delta,
        )

        status = "PASS" if allowed == expected else "FAIL"
        print(
            f"[{status}] {label:15s} | "
            f"delta={delta: .6f} | "
            f"allowed={allowed}"
        )

    print("\nActive policy:")
    print(ContextPolicy.describe())

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
