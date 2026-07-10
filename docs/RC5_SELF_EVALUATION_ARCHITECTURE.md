# RC5 Self Evaluation Architecture

RC5 self-evaluation measures behavior against purpose instead of treating confidence as truth.

Evaluation dimensions:

- task outcome
- purpose alignment
- governance compliance
- communication quality
- evidence quality
- efficiency
- metric coverage

Missing metrics are classified separately from capability failures. Isolated low-severity events are not treated as confirmed deficits. Governance violations are always surfaced as protected failures.

The output is a `PurposeAlignmentEvaluation`, which feeds deficit detection but does not authorize code changes or memory writes.
