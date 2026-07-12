# SOL-Style Adversarial Audit

## Role and Independence Limit

This is a SOL-style adversarial audit performed by the requested single TERRA-led cycle. It is not an independently switched SOL-model result. The audit deliberately preceded edits and treats that lack of model independence as a confidence limitation.

## Executive Assessment

The prior behavioral closure recommendation was supported for deterministic, governed state handling, but not for real local-model operation or responsive desktop behavior. The prior campaign honestly recorded zero model calls, yet its readiness headline could be misread as stronger end-to-end model integration than the code provided.

Audit verdict: `TARGETED_REPAIRS_REQUIRED`.

The controller and governance envelope were sound enough for bounded repair. No governance blocker, hidden persistence path, provider authority path, or automatic memory-write path was found in the audited live path.

## Findings

### SOL-001: Live local-model execution was unreachable

- Classification: runtime defect, model-integration defect
- Severity: HIGH
- Confidence: HIGH
- Affected subsystem: live runtime bridge and desktop UI
- Evidence: `handle_live_chat` ended ordinary live turns with `route_message(..., execute_local_model=False)`. The live UI returned immediately from that branch, bypassing its non-live pending local-model handling. A direct live probe sent an unfamiliar question then `yes`; the answer route was `social_conversation`, with zero model calls.
- Reproduction: start a live session; send `Explain the concept of octarine in practical terms.`; send `yes`; inspect route and manager call count.
- Smallest responsible repair: retain a session-scoped, explicitly approved local-model request; execute exactly that request through the existing local lane; record the result as a controller event and synchronize residency.
- Required tests: consent, explicit execution, cross-action ambiguity, unavailable-model recovery, controller residency synchronization.
- TERRA action: implement now.

### SOL-002: Wikipedia retrieval and newly reachable inference would block the Tk event thread

- Classification: runtime defect, operator UX problem, performance risk
- Severity: HIGH
- Confidence: HIGH
- Affected subsystem: desktop live UI
- Evidence: the live UI called `handle_live_chat` inline. The default Wikipedia transport can wait for a lock, use an 8-second URL timeout, and retry twice with backoff. A single operator turn could therefore hold the UI for roughly 25 seconds. Real inference also takes several seconds.
- Reproduction: inspect `DeltaApp._send_chat` and `_default_wikipedia_transport`; run a slow retrieval or model turn from the UI.
- Smallest responsible repair: move the complete live turn into a worker, return results through a main-thread queue, disable only new text entry while work is in flight, and queue lifecycle controls to the next safe turn boundary.
- Required tests: UI smoke with retrieval plus pause and inference plus suspend; preserve no concurrent session mutation.
- TERRA action: implement now.

### SOL-003: Model residency telemetry omitted the effective process GPU layer setting

- Classification: reporting overclaim, performance risk
- Severity: MEDIUM
- Confidence: HIGH
- Affected subsystem: provider manager telemetry
- Evidence: the real pilot used `DELTA_N_GPU_LAYERS=-1` and GPU memory rose to about 7.2 GB, while `ProviderLoadState.n_gpu_layers` reported `null`. `ModelSession` read the environment variable but `ProviderManager.status` did not.
- Reproduction: set `DELTA_N_GPU_LAYERS=-1`, load a local model, compare `nvidia-smi` and `ProviderManager.status()`.
- Smallest responsible repair: have the manager report the same process-scoped override used by the session when no capability profile provides a value.
- Required tests: fake-runner status with `DELTA_N_GPU_LAYERS=-1`.
- TERRA action: implement now.

### SOL-004: The broad behavioral campaign still does not invoke real local models

- Classification: reporting limitation, model-integration limitation
- Severity: MEDIUM
- Confidence: HIGH
- Evidence: the 373-scenario campaign reports `model_call_count: 0`. Its controller events and residency checks are useful, but do not validate a real Llama/Mistral invocation.
- Smallest responsible repair: do not force models into deterministic scenarios. Add a separate bounded real-model pilot and later add fake-manager campaign cases for correlation and recovery.
- Required tests: Llama -> Mistral -> Llama pilot; unavailable-model path; residency assertion.
- TERRA action: validate now; retain campaign extension as next work.

### SOL-005: Multi-hour human operation remains unproven

- Classification: performance risk, readiness limitation
- Severity: MEDIUM
- Confidence: HIGH
- Evidence: the full harness took about 199 seconds and the UI smoke was compact. There is no several-hour operator trace with real local inference, external process metrics, or interruption history.
- Smallest responsible repair: controlled operator pilot, not more fixture volume.
- Required tests: multi-hour scripted/operator session with sampled CPU, working set, GPU memory, queue depth, notifications, model switches, and recovery.
- TERRA action: defer; this is an operational proof, not a safe same-commit feature.

### SOL-006: The local-model consent response is semantically duplicated in the UI

- Classification: operator UX problem
- Severity: LOW
- Confidence: HIGH
- Evidence: the live UI smoke showed a generic `Would you like me to ask a local reasoning model?` sentence followed by the model-specific offer and reply instruction. Both originate in the conversation renderer.
- Smallest responsible repair: make one component own the consent wording while retaining the model name and explicit approval boundary.
- Required tests: rendered consent prompt contains one semantic question and one reply instruction.
- TERRA action: defer; it does not weaken governance or block the pilot.

### SOL-007: Registry count conflates aliases, physical model specifications, and usable models

- Classification: architecture risk, reporting limitation
- Severity: LOW
- Confidence: HIGH
- Evidence: registry inspection returned 15 entries, 10 unique specifications, 5 usable specifications, and 5 aliases. The self-model labels this as `Available local model entries`, which is technically true but easy to overread as usable resident choices.
- Smallest responsible repair: expose separate `registry_entries`, `unique_model_specs`, and `usable_model_specs` counts.
- Required tests: alias and unusable-path fixture.
- TERRA action: defer to model-registry consolidation.

## Rejected Suspicions

- Wikipedia transport was not unrestricted: it remained text-only, read-only, throttled, bounded to one page per retrieval turn, and showed provenance.
- Failed retrieval did not create a candidate or memory write in focused tests and the full harness.
- Promotion approval did not write canonical or noncanonical memory automatically.
- Bare approval among multiple promotion candidates remained ambiguous rather than silently selected.
- Suspension blocked retrieval and local-model offers in the existing path.
- No runtime commit, push, deployment, permission expansion, or purpose mutation path was found in the audited live bridge.

## Campaign Oracle Critique

The 1,500 turns are meaningful state-space evidence, but they are not independent proof of real inference or real asynchronous UI. Route and phrase assertions still cover some implementation-shaped expectations. The new evidence must therefore remain layered: deterministic campaign, focused fake-manager tests, bounded real-model pilot, and desktop smoke.

## Prioritized Repair Plan

1. Repair SOL-001 and SOL-002 together: a local-model request must be explicit, correlated, serialized, and UI-nonblocking.
2. Repair SOL-003 so measurements describe the actual pilot configuration.
3. Validate SOL-004 with a small real-model pilot instead of expanding automatic inference.
4. Leave SOL-005 through SOL-007 as explicit risks or consolidation work.

## Work Not Recommended

- Do not grant the controller automatic local-model invocation.
- Do not add web surfaces, provider authority, hidden persistence, runtime commit/push authority, or background threads that mutate session state.
- Do not attempt a broad router or milestone naming rewrite in this repair commit.
