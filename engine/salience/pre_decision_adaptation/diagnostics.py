# engine/salience/pre_decision_adaptation/diagnostics.py

from typing import Optional

from .psmem import PSMem


def dump_psm_summary(psmem: PSMem) -> None:
    """
    Print a high-level summary of PSMem state.

    This function is intended for debugging and inspection only.
    It must not be called inside the runtime step loop.
    """
    stats = psmem.stats()

    print("[PSMem]")
    print(f"  contexts: {stats['contexts']}")
    print(f"  records: {stats['records']}")
    print(f"  max_records_per_context: {stats['max_records_per_context']}")
    print(f"  gain: {stats['gain']}")
    print(f"  max_bias: {stats['max_bias']}")


def dump_context(psmem: PSMem, context_id: str) -> None:
    """
    Print stored deliberation records for a specific context.

    Useful for verifying that learning is occurring without
    affecting decision authority.
    """
    buf = psmem._records.get(context_id)

    print(f"[PSMem] context='{context_id}'")

    if not buf:
        print("  (no records)")
        return

    for i, rec in enumerate(buf):
        print(
            f"  #{i:02d} "
            f"cost={rec.deliberation_cost:.3f} "
            f"instability={rec.instability:.3f} "
            f"steps=[{rec.step_start}->{rec.step_end}]"
        )


def dump_bias(psmem: PSMem, context_id: str) -> None:
    """
    Print the computed salience bias for a context.
    """
    bias = psmem.get_bias(context_id)
    print(f"[PSMem] bias(context='{context_id}') = {bias:.4f}")
