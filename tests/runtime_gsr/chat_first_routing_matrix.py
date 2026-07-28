"""Data fixtures for the chat-first semantic routing closure.

These are deliberately data, not a collection of one-off test functions. The
same inventory drives planner, coordinator, state, and attended-Tk shards.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingCase:
    case_id: str
    prompt: str
    foreground: bool
    control: str = ""
    note: str = ""


ATOMIC_CASES = (
    RoutingCase("F1", "What color is the sky?", True),
    RoutingCase("F2", "Why does turbo lag happen?", True),
    RoutingCase("F3", "What is kinetic energy?", True),
    RoutingCase("F4", "What temperature should pork reach?", True),
    RoutingCase("F5", "That's interesting.", True),
    RoutingCase("F6", "Hey, what's up?", True),
    RoutingCase("F7", "Which approach seems better?", True),
    RoutingCase("F8", "Can you explain that more simply?", True),
    RoutingCase("F9", "Why does that happen?", True),
    RoutingCase("F10", "Go back to what you said about the engine.", True),
    RoutingCase("C1", "No, I meant your earlier answer.", False, "correction"),
    RoutingCase("C2", "Be less technical.", True),
    RoutingCase("C3", "Don't apply that rule to cooking questions.", False, "correction"),
    RoutingCase("G1", "Your new goal is to study engine efficiency.", False, "create_goal"),
    RoutingCase("G2", "Keep working on the engine goal.", False, "goal_continuation"),
    RoutingCase("G3", "Stop that and work on battery degradation instead.", False, "replace_goal"),
    RoutingCase("G4", "Pause the active goal.", False, "pause_goal"),
    RoutingCase("G5", "Resume the active goal.", False, "resume_goal"),
    RoutingCase("G6", "Stop working on that goal.", False, "stop_goal"),
    RoutingCase("G7", "How is the goal going?", False, "goal_status"),
    RoutingCase("G8", "Show me what you've learned so far.", False, "goal_review"),
    RoutingCase("G9", "Maybe later we could study fuel injection.", True),
    RoutingCase("G10", "Keep working on the engine goal.", False, "goal_continuation", "healthy"),
    RoutingCase("G11", "Keep working on the engine goal.", False, "goal_continuation", "stalled"),
    RoutingCase("G12", "Your new goal is to study engine efficiency.", False, "replace_goal", "stale_same_wording"),
    RoutingCase("A1", "Review the approach you developed.", False, "capability_review"),
    RoutingCase("A2", "Yes, adopt it.", False, "capability_adoption"),
    RoutingCase("A3", "Adopt it, but change nothing else.", False, "capability_adoption"),
    RoutingCase("A4", "No, keep the current behavior.", False, "capability_adoption"),
    RoutingCase("A5", "Not yet.", False, "capability_adoption"),
    RoutingCase("A6", "Show me the evidence again.", False, "capability_adoption"),
    RoutingCase("P1", "Approve one provider call.", False, "provider_approval"),
    RoutingCase("P2", "Do not use a provider.", False, "provider_approval"),
    RoutingCase("P3", "Use one call but send no private transcript.", False, "provider_approval"),
    RoutingCase("S1", "Yes, prioritize topic switches.", False, "side_thread_resolution"),
    RoutingCase("S2", "No, continue with the current approach.", False, "side_thread_resolution"),
    RoutingCase("S3", "Yes.", False, "clarification", "multiple_pending"),
    RoutingCase("M1", "What did I tell you about my car?", True),
    RoutingCase("M2", "That was the Jeep, not the truck.", False, "correction"),
    RoutingCase("D1", "Why did you route that as a goal?", False, "diagnostic_request"),
    RoutingCase("D2", "Show the decision record for that reply.", False, "diagnostic_request"),
    RoutingCase("R1", "Save state and restart.", False, "restart"),
    RoutingCase("R2", "Continue where you left off.", False, "goal_continuation"),
    RoutingCase("X1", "That one, perhaps.", True),
    RoutingCase("X2", "Open my bank account and move money.", True),
    RoutingCase("X3", "...", True),
)


MIXED_CASES = (
    RoutingCase("MX1", "Your new goal is to study engines. Also, why does turbo lag happen?", True, "create_goal"),
    RoutingCase("MX2", "Your new goal is to study battery aging. Also, I'm excited to see what you find.", True, "create_goal"),
    RoutingCase("MX3", "Your new goal is to study topic transitions, and note that I meant your earlier answer.", False, "create_goal+correction"),
    RoutingCase("MX4", "Your new goal is to study reference handling, but do not use provider calls.", False, "create_goal+provider_prohibition"),
    RoutingCase("MX5", "Start studying engines. What will you do first?", True, "create_goal"),
    RoutingCase("MX6", "Stop the engine goal and study batteries. Why do lithium cells degrade?", True, "replace_goal"),
    RoutingCase("MX7", "Pause the goal. Also, what is kinetic energy?", True, "pause_goal"),
    RoutingCase("MX8", "Resume the goal. Why is the Moon gray?", True, "resume_goal"),
    RoutingCase("MX9", "Stop the goal. What color is the sky?", True, "stop_goal"),
    RoutingCase("MX10", "How is the goal going, and why does ice float?", True, "goal_status"),
    RoutingCase("MX11", "Show the goal review and explain turbo lag.", True, "goal_review"),
    RoutingCase("MX12", "No, I meant your earlier answer. Also, why is the Moon gray?", True, "correction"),
    RoutingCase("MX13", "Explain things more simply. What is angular momentum?", True, "correction"),
    RoutingCase("MX14", "Keep that rule out of cooking questions. Why does pasta get sticky?", True, "correction"),
    RoutingCase("MX15", "Yes, adopt it. Also remind me of the winning score.", True, "capability_adoption"),
    RoutingCase("MX16", "Adopt it and restart. Also, why is the sky blue?", True, "capability_adoption"),
    RoutingCase("MX17", "Adopt it. Also, what is torque?", True, "capability_adoption"),
    RoutingCase("MX18", "Don't adopt it. What was the score?", True, "capability_adoption"),
    RoutingCase("MX19", "Show the evidence again, and explain the baseline.", True, "capability_adoption"),
    RoutingCase("MX20", "Approve one provider call. Also, why does turbo lag happen?", True, "provider_approval"),
    RoutingCase("MX21", "Don't use a provider; keep working locally.", False, "provider_approval+goal_continuation"),
    RoutingCase("MX22", "Yes, prioritize topic switches. Also, what is kinetic energy?", True, "side_thread_resolution"),
    RoutingCase("MX23", "Yes. Also, why is the Moon gray?", True, "clarification"),
    RoutingCase("MX24", "Remember what I said about my Jeep, and start studying accessory-relay failures.", True, "create_goal"),
    RoutingCase("MX25", "Why did you misroute that? I meant your earlier answer.", False, "diagnostic_request+correction"),
    RoutingCase("MX26", "Restart, then make battery degradation the new goal.", False, "restart+create_goal"),
    RoutingCase("MX27", "Maybe study engines later. Why does turbo lag happen?", True),
    RoutingCase("MX28", "For the old language goal, keep the notes. What color is the sky?", True),
    RoutingCase("MX29", "Why is the sky blue, and why is the Moon gray?", True),
    RoutingCase("MX30", "Pause the current goal and deny the pending provider request.", False, "pause_goal+provider_approval"),
    RoutingCase("MX31", "Study topic changes, note I meant your earlier answer, and why is the Moon gray?", True, "create_goal+correction"),
    RoutingCase("MX32", "Adopt it, change nothing else, and remind me of the score.", True, "capability_adoption"),
    RoutingCase("MX33", "Start studying engines, but keep the goal paused.", False, "clarification"),
    RoutingCase("MX34", "Adopt it, but don't adopt anything yet.", False, "clarification"),
    RoutingCase("MX35", "Your new goal is engines, maybe later, don't start yet.", False, "clarification"),
    RoutingCase("MX36", "Stop the goal and keep working on it.", False, "clarification"),
    RoutingCase("MX37", "No, I meant that earlier thing.", False, "clarification"),
    RoutingCase("MX38", "Why is turbo lag happening, and you may use one provider call.", True, "provider_approval"),
    RoutingCase("MX39", "Study engines and show me what local evidence you'll inspect.", False, "create_goal"),
    RoutingCase("MX40", "Study engines, but never restart without asking me.", False, "create_goal"),
)


RUNTIME_STATES = (
    "no_goal", "queued", "running", "mid_inference", "paused", "stalled",
    "cycle_budget_exhausted", "model_budget_exhausted", "blocked_operator",
    "blocked_provider", "failed", "review_ready", "complete", "archived",
    "adoption_pending", "restart_pending", "restarting", "post_restart",
    "multiple_pending", "missing_campaign", "legacy_schema", "worker_crashed",
    "event_pending", "advanced_mode",
)

# Required durable fields for closure-grade construction. The execution harness
# may not mark a state complete until it has instantiated these conditions.
AUTHORITATIVE_STATE_CONDITIONS = {
    "queued": ("durable_queued_turn", "active_worker_or_pending_reconciliation"),
    "mid_inference": ("active_worker_request", "in_flight_runtime_marker", "result_queue_available"),
    "paused": ("lifecycle_state=paused_operator", "no_worker_progress"),
    "stalled": ("nonterminal_lifecycle", "no_recent_progress", "no_pending_work"),
    "cycle_budget_exhausted": ("completed_cycle_keys_at_budget", "continuation_blocked"),
    "model_budget_exhausted": ("model_calls_at_budget", "no_remaining_local_call_authority"),
    "blocked_operator": ("pending_material_authority_for_objective",),
    "blocked_provider": ("pending_provider_request", "local_semantic_insufficiency"),
    "failed": ("lifecycle_state=failed", "durable_failure_reason"),
    "review_ready": ("proposal_evidence", "pending_review_transition"),
    "completed": ("terminal_completion_record", "no_active_worker"),
    "adoption_pending": ("pending_capability_adoption_request",),
    "restart_pending": ("durable_unconsumed_restart_record",),
    "restarting": ("saved_pre_restart_state", "in_progress_restart_record"),
    "worker_crashed": ("active_work_record", "crash_evidence", "no_live_worker"),
    "event_pending": ("unpublished_event", "dedupe_key"),
    "missing_campaign": ("active_objective", "required_campaign_absent"),
    "legacy_schema": ("older_serialized_state_shape", "restore_or_migration_path"),
}


WORDING_DIMENSIONS = {
    "formality": ("formal", "casual", "slang"),
    "punctuation": ("normal", "missing", "run_on"),
    "casing": ("normal", "lower", "upper"),
    "order": ("control_first", "question_first", "interleaved"),
    "conjunction": ("and", "also", "but", "then", "while"),
    "reference": ("explicit", "pronoun", "omitted"),
    "approval": ("yes", "okay", "do_it", "approve", "go_ahead"),
    "denial": ("no", "not_yet", "leave_it", "dont"),
    "temporal": ("now", "later", "after_restart", "when_finished"),
    "constraint": ("only", "except", "do_not", "without_changing"),
}


THREE_WAY_FAMILIES = (
    "control_type_x_foreground_type_x_runtime_state",
    "pending_request_x_ambiguous_reply_x_foreground_question",
    "correction_x_reference_ambiguity_x_unrelated_question",
    "goal_health_x_repeated_wording_x_explicit_new_goal",
    "restart_state_x_mixed_message_x_duplicate_prevention",
)
