# Failure Recovery

Queue growth, timeouts, invalid transitions, model unavailability, Wikipedia failure, and repeated exceptions move the controller toward `DEGRADED`, `PAUSED_FOR_REVIEW`, `SUSPENDED`, or `FAILED_SAFE`. Shutdown remains available at all times. Recovery returns to `IDLE` only through explicit controller transitions.

## Health Inputs

The controller checks event queue size, model availability, Wikipedia availability, cycle timeout, repeated exceptions, stale objectives, and resource limit events. It records process CPU time, active Python threads, and best-effort Windows working-set metrics without requiring `psutil`.

## Degraded Mode

When degraded, the controller stops automatic initiative work and preserves the audit trail. The operator can pause, suspend, or shut down. Unknown action types or invalid lifecycle transitions fail closed.

## Recovery

Recovery is explicit and bounded. The controller may return to `IDLE` after a recoverable condition clears, but it does not retry external retrieval, model execution, sandbox work, or persistence automatically.
