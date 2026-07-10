# RC5 Upgrade Governance and RC4 Handoff

RC5 does not implement upgrades directly. When a validated deficit and acquisition strategy justify work, RC5 prepares an `UpgradeProposal` and an RC4 handoff artifact.

The handoff requires:

- operator review
- RC4 authorization
- candidate patch generation
- controlled workspace validation
- rollback evidence
- comparative evaluation

The handoff explicitly prohibits automatic provider calls, self-approval, and direct live mutation. RC5 therefore decides what improvement may be worth proposing; RC4 governs whether and how that proposal can become code.
