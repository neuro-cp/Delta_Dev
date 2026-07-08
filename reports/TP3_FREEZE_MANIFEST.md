# TP3 Freeze Manifest

- repo_commit: `233e8a7d6803e091441631d14f5cf80a3e01dab6`
- branch: `codex/delta-cognitive-core`
- runtime_phase: TP3 independent verification freeze

## Enabled Capabilities

- fixture-only deterministic verification
- report-only independent scoring
- local answer route for TP3 status

## Blocked Capabilities

- model training
- fine tuning
- weight updates
- provider calls
- canonical writes
- live memory mutation
- live knowledge mutation
- scheduler/background workers
- action execution
- HYB1 promotion

## Verification Criteria

- corpus hashes match manifest
- selected TP0-TP2 report hashes remain readable
- TP2 replay matches frozen expected values
- falsification cases block unsafe interpretations
- rollback remains stable
- no prohibited capability flag becomes true
