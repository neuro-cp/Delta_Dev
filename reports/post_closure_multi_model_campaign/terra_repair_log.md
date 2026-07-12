# TERRA Repair Log

## SOL-001 - CONFIRMED_AND_REPAIRED

The live session now holds `pending_local_model_request` only after the existing route asks for local-model consent. The request contains the target message, selected lane, model identity, bounded lifetime, and explicit operator-approval classification.

Approval behavior is intentionally narrow:

- with only the pending model request, `yes` runs exactly that request;
- with both a promotion review and a model request, bare `yes` returns `live_operator_action_ambiguous`;
- `ask the local model` explicitly chooses local inference;
- an unavailable local model returns `live_local_model_unavailable`, clears the request, and does not retry automatically.

Successful calls add a `MODEL_READY` controller event and update controller residency from the actual provider-manager status. Failures add `MODEL_UNAVAILABLE` and preserve the no-provider/no-write boundary.

## SOL-002 - CONFIRMED_AND_REPAIRED

The desktop UI now sends live turns through one daemon worker and a `queue.Queue` consumed by Tk's normal event loop. Text entry is disabled only while the one turn is running. Lifecycle controls remain responsive and are queued in order for the next safe boundary, preventing the worker's session result from overwriting a simultaneous control mutation.

The repair deliberately does not claim cancellation of an already-issued HTTP or inference call. Pause or Suspend takes effect after that bounded operator turn completes, which is the explicit state-transition boundary.

## SOL-003 - CONFIRMED_AND_REPAIRED

`ProviderManager._gpu_layers_for` now reports `DELTA_N_GPU_LAYERS` when neither direct manager configuration nor a capability profile supplies a setting. The provider status now matches the model session's effective configuration for the bounded pilot.

## SOL-004 - CONFIRMED_BY_PILOT

No model was injected into the deterministic campaign. Instead, the real pilot executed the actual code path with actual GGUF files and an explicit operator gate. That choice preserves deterministic state handling while proving the end-to-end integration separately.

## Deferred Findings

- SOL-005: multi-hour real operator proof.
- SOL-006: duplicate consent wording in a low-risk UI branch.
- SOL-007: registry entry/alias/usable count semantics.
