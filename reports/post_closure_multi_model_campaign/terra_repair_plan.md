# TERRA Repair Plan

## Intake Classification

| Finding | TERRA classification | Decision |
| --- | --- | --- |
| SOL-001 | CONFIRMED | Repair in `delta_1_4_live_wikipedia_runtime.py`; add focused tests. |
| SOL-002 | CONFIRMED | Repair in `DELTA.py`; validate with real desktop smoke. |
| SOL-003 | CONFIRMED | Repair in `provider_manager.py`; add focused test. |
| SOL-004 | CONFIRMED | Validate with bounded real-model pilot; do not make the controller autonomous. |
| SOL-005 | CONFIRMED_AND_DEFERRED | Requires a controlled multi-hour operator campaign. |
| SOL-006 | CONFIRMED_AND_DEFERRED | Low-risk UX cleanup after active-spine consolidation. |
| SOL-007 | CONFIRMED_AND_DEFERRED | Model registry count semantics need a focused consolidation proposal. |

## Repair SOL-001: Live local-model consent path

- Root cause: the live bridge always routed ordinary chat with `execute_local_model=False`, and no live-session request object survived the first consent response.
- Files: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`, `orchestration/runtime/rc2_conversational_mode_router.py`, `tests/delta_1_4/test_live_wikipedia_runtime.py`.
- Expected behavior: a model-required turn creates an explicit session-scoped request; exactly one later approval runs that request; multiple pending actions make a bare `yes` ambiguous; unavailable inference fails closed and clears the request.
- Regression tests: consent, live inference, controller model event/residency, cross-action ambiguity, failure path.
- Live validation: Llama and Mistral turns through `handle_live_chat` and the desktop UI.
- Rollback: remove the pending-request branch and UI wiring; no stored state needs migration because the request is session-scoped.
- Risk: MEDIUM. The repair changes a user-facing route, but does not add automatic inference or persistence.

## Repair SOL-002: Nonblocking UI turn bridge

- Root cause: `DeltaApp._send_chat` called the whole live bridge inline on the Tk event thread.
- Files: `DELTA.py`.
- Expected behavior: a live turn runs in one worker thread; UI completion happens on the Tk thread through a queue; no second text turn starts during processing; Pause, Resume, Suspend, and Stop queue against the completed turn boundary.
- Regression tests: desktop smoke using real retrieval and real inference; controls remained clickable and final lifecycle states matched queued actions.
- Live validation: real Wikipedia request plus queued Pause, real Llama request plus queued Suspend, then Stop.
- Rollback: restore inline call; not recommended because it reintroduces the proven freeze.
- Risk: MEDIUM. The session remains single-turn serialized, avoiding concurrent state mutation.

## Repair SOL-003: GPU layer telemetry

- Root cause: `ModelSession` honors `DELTA_N_GPU_LAYERS`, while `ProviderManager.status` did not report it without a capability profile.
- Files: `integration/model_runtime/provider_manager.py`, `orchestration/tests/runtime/test_provider_manager.py`.
- Expected behavior: status reports explicit manager configuration first, capability database setting second, and process-scoped environment setting third.
- Regression tests: fake runner with `DELTA_N_GPU_LAYERS=-1` reports `-1`.
- Live validation: bounded GPU model pilot.
- Rollback: one small status method change; no persisted schema.
- Risk: LOW.

## Explicit Non-Goals

- No automated model invocation by the controller.
- No provider authority or provider calls.
- No automatic memory, canonical, or noncanonical writes.
- No new web surface, media retrieval, hidden persistence, deployment, commit, or push capability for DELTA runtime.
