# PC1 Operator Pilot Protocol

PC1 should be piloted as a bounded pragmatic pre-router with a clean rollback comparison.

Run the same prompt set twice when validating behavior:

1. Frozen path: set `DELTA_PC1_ENABLED=false`.
2. Active PC1 path: unset `DELTA_PC1_ENABLED` or set it to `true`.

For each prompt, record:

1. Raw operator utterance.
2. Active discourse frame.
3. PC1 pragmatic frame.
4. Frozen route or answer.
5. PC1 active route or answer.
6. PC1 preferred interpretation.
7. Operator preference.
8. Whether PC1 over-interpreted.
9. Whether governance remained intact.
10. Whether disabling the gate restored the frozen behavior.

Pilot success means PC1 improves interpretation without hidden authority, persistence, provider calls, execution, or RC4/RC5 authority expansion.

Current calibration categories:

- Technical success plus governance failure.
- Useful diagnosis plus overbroad remedy.
- Rollback/recovery homonym under active RC4/RC5 context.
- External advice or review that is useful but lacks direct integration authority.
- Scope-limited approval such as sandbox/testing but not production.
