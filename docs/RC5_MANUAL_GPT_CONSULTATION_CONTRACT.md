# RC5 Manual GPT Consultation Contract

RC5 supports manual external consultation by packet, not by API.

The operator may copy a `DevelopmentConsultationPacket` into an external model and paste back advice. The packet is compact and includes:

- current purpose criterion
- observed deficit
- supporting evidence and counterevidence
- architecture summary
- hard constraints
- prohibited changes
- requested output
- token budget
- omitted context

Imported advice is advisory-only. RC5 validates the advice against safety boundaries and rejects instructions such as automatic API calls, self-approval, governance bypass, or immediate training.

The contract is transport-neutral: a future governed API gateway could replace manual copy/paste without redesigning the developmental loop. That future transport would still need operator authorization, budgeting, audit logs, and RC4-compatible governance.
