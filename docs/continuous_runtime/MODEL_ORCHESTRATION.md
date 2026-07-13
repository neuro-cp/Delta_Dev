# Model Orchestration

The controller reads the real local model registry and lane router. Default conversation uses `meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m`, planning uses `mistral-7b-instruct-v0-3-gguf-mistral-7b-instruct-v0-3-q4-k-m`, and development analysis uses `meta-llama-3-1-8b-instruct-gguf-meta-llama-3-1-8b-instruct-q4-k-m`. ProviderManager remains serial with one resident local model maximum.

## Actual Inventory

The registry exposes multiple GGUF models and aliases rather than exactly two hardcoded models. The controller therefore reports actual registry state, selected lane models, resident model ID, resident lane, and residency status.

## Routing Policy

Deterministic subsystems answer without a model for lifecycle status, authority classification, capability reporting, Wikipedia budget exhaustion, and cached evidence discussion. Local models remain useful for synthesis, planning, hypothesis generation, coding proposals, ambiguity resolution, and deeper developmental reflection.

## Residency Policy

The existing `ProviderManager` is the authority for local model residency. It is serial and keeps at most one local GGUF model resident at a time. The continuous controller observes and reports this state; it does not keep multiple models loaded or invoke inference from idle reflection.

## Validation Boundary

The bounded campaign observes model-ready events and lane selection. Repeated real inference, model switching under pressure, failed invocation recovery, and planning-to-conversation handoff still require a controlled long-horizon pilot.
