from __future__ import annotations

"""
Certification test: sleep orchestration with inspection diff input.

Verifies:
- Inspection diff can bias sleep profile selection
- Eligibility logic remains unchanged
- Orchestration remains policy-only
"""

from engine.sleep.orchestration.sleep_orchestrator import SleepOrchestrator
from engine.sleep.orchestration.sleep_trigger import SleepTrigger
from engine.sleep.orchestration.sleep_request import SleepRequest
from engine.sleep.orchestration.sleep_profile import SleepProfile

from engine.inspection.diffing.diff_report import DiffReport


def test_sleep_orchestration_prefers_nrem_on_cognition_change() -> None:
    # --------------------------------------------------
    # Sleep profiles (policy inputs)
    # --------------------------------------------------
    profiles = {
        "nap": SleepProfile(
            name="nap",
            allowed_replay_modes=["wake"],
            max_episodes=1,
            description="Light replay only",
        ),
        "nrem_heavy": SleepProfile(
            name="nrem_heavy",
            allowed_replay_modes=["nrem"],
            max_episodes=5,
            description="Consolidation-focused sleep",
        ),
        "mixed": SleepProfile(
            name="mixed",
            allowed_replay_modes=["nrem", "rem"],
            max_episodes=4,
            description="Balanced sleep cycle",
        ),
    }

    orchestrator = SleepOrchestrator(
        profiles=profiles,
        min_interval=10,
    )

    # --------------------------------------------------
    # Sleep request (idle trigger would normally select nap)
    # --------------------------------------------------
    request = SleepRequest(
        trigger=SleepTrigger(
            trigger_type="idle",
            source="system",
        ),
        requested_step=100,
    )

    # --------------------------------------------------
    # Inspection diff indicating cognition changed
    # --------------------------------------------------
    diff = DiffReport(
        replay_changed=False,
        cognition_changed=True,
        hypothesis_diff=None,
    )

    # --------------------------------------------------
    # Decision
    # --------------------------------------------------
    decision = orchestrator.decide(
        request=request,
        current_step=200,
        last_sleep_step=None,
        inspection_diff=diff,
    )

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert decision is not None
    assert decision.profile_name == "nrem_heavy"
    assert decision.selected_replay_modes == ["nrem"]
    assert decision.episode_budget == 5
    assert "cognition_changed=True" in decision.justification

    print("\n=== SLEEP ORCHESTRATION WITH DIFF ===")
    print("Selected profile:", decision.profile_name)
    print("Replay modes:", decision.selected_replay_modes)
    print("Justification:", decision.justification)
