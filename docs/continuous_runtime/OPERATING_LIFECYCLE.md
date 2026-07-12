# Operating Lifecycle

Supported states: `BOOT`, `INITIALIZING`, `LOADING_STATE`, `IDLE`, `EVENT_PENDING`, `OBSERVING`, `ASSESSING`, `REFLECTING`, `PLANNING`, `WAITING_FOR_OPERATOR`, `RUNNING_APPROVED_LOCAL_WORK`, `VALIDATING`, `JOURNALING`, `PAUSED`, `SUSPENDED`, `DEGRADED`, `RECOVERING`, `SHUTTING_DOWN`, `SHUTDOWN`.

Default wake mode is `EVENT_DRIVEN`. `BOUNDED_BACKGROUND` may be enabled by operator policy, while `PAUSED` and `SUSPENDED` fail closed. Illegal transitions raise errors.

## Wake Modes

- `MANUAL`: only explicit operator or test calls advance the controller.
- `EVENT_DRIVEN`: default; wake only when an event arrives.
- `BOUNDED_BACKGROUND`: permits low-frequency idle reflection.
- `EXPERIMENTAL_CONTINUOUS`: reserved for future operator-approved trials.
- `PAUSED`: no initiative generation.
- `SUSPENDED`: fail-closed review state.

## Cycle Bounds

Each cycle enforces a maximum event batch size, cycle duration target, generated
initiative count, journal entries, model calls, and Wikipedia calls. The current
controller sets model and Wikipedia calls per cycle to zero because model
execution and retrieval are handled by explicit governed paths, not idle
reflection.

## Shutdown

Shutdown is explicit: `SHUTTING_DOWN -> SHUTDOWN`. The controller clears its
queue and remains inspectable through the final snapshot.
