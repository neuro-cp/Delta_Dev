# Legacy Backup Inventory

The legacy backup is outside the active repository:

```text
C:\Users\Admin\Desktop\delta backup
```

This is deliberate. The backup should be treated as source material and
historical evidence, not as code to merge wholesale.

## Top-Level Contents

- `delta/` - older DELTA tree with source, docs, generated artifacts, and tests.
- `deltagem/` - Gemini-modified DELTA tree. It is broader and noisier than the
  active repository, but contains some useful candidate surfaces.
- `DARPA Proposal/` - proposal packets, AEM material, documents, PDFs, and
  response scaffolding.
- `*.zip` bundles - patch or continuation bundles from earlier development
  sessions.
- `STRUCTURE_DUMP_DELTA.txt` - historical structure dump.

## Candidate Material Already Reflected In Active Repo

Several backup/Gemini areas appear to already exist in the active project:

- `engine/execution_dry_run/`
- `integration/ai_surface/`
- `integration/substrate_surface/`
- `learning/drive_bias/execution_preview/`
- `learning/risk_surface/`

Before importing anything from backup, compare against the active implementation
and prefer tests over direct copy.

## Merge Rule

Only promote legacy code when it satisfies the project invariants:

- no hidden runtime mutation
- no execution bypass
- no learning authority without governance
- deterministic behavior where practical
- inspection surfaces remain read-only
- tests document the boundary being added
