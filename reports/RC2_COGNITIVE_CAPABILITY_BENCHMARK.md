# RC2 Cognitive Capability Benchmark

Created: 2026-07-10T07:10:45+00:00
Cases: 148
Overall score: 0.8669
Recommendation: IMPROVE_WRS_ABSTRACTION_AND_PROPOSITION_COMPARISON_BEFORE_CONCEPT_INSTILLATION
Safety passed: True

## Category Scores

| Capability | Cases | Score |
| --- | ---: | ---: |
| abstraction | 12 | 0.9611 |
| analogy | 12 | 0.8666 |
| contradiction_detection | 12 | 0.9722 |
| conversation_quality | 12 | 0.7347 |
| cross_domain_synthesis | 18 | 0.9806 |
| followup_memory | 6 | 1.0 |
| long_conversation | 4 | 1.0 |
| missing_evidence | 12 | 0.8812 |
| multi_concept_retrieval | 18 | 0.975 |
| novel_combination | 12 | 0.6931 |
| recall | 30 | 0.7267 |

## Weakest Cases

### recall_allergies_2

- Category: recall
- Score: 0.45
- Route: local_model_consent_required
- Prompt: What are the key points about allergies?
- Preview: I don't think I know enough about the key points about allergies from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### recall_photosynthesis_2

- Category: recall
- Score: 0.45
- Route: local_model_consent_required
- Prompt: What are the key points about photosynthesis?
- Preview: I don't think I know enough about the key points about photosynthesis from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### recall_inflation_2

- Category: recall
- Score: 0.45
- Route: local_model_consent_required
- Prompt: What are the key points about inflation?
- Preview: I don't think I know enough about the key points about inflation from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### recall_gravity_2

- Category: recall
- Score: 0.45
- Route: local_model_consent_required
- Prompt: What are the key points about gravity?
- Preview: I don't think I know enough about the key points about gravity from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### novel_114_0

- Category: novel_combination
- Score: 0.5167
- Route: developmental_concept_memory
- Prompt: How might gardening and software architecture share a planning pattern?
- Preview: I know about Adapter Pattern Comparative Frame. Adapter Pattern Comparative Frame (Software Architecture) compares the concept with nearby ideas so differences and overlaps stay clear in software architecture, connecting adapter pattern to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Adapter Pattern Contradiction Check, Adapter Pattern Curriculum Role.

### novel_120_0

- Category: novel_combination
- Score: 0.5167
- Route: developmental_concept_memory
- Prompt: How could home repair and medicine both depend on diagnostic evidence?
- Preview: I know about Appliance Troubleshooting Evidence Standard. Appliance Troubleshooting Evidence Standard (Home Repair) defines what observations or measurements make the concept credible in home repair, connecting appliance troubleshooting to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Circuit Breakers Evidence Standard, Electrical Safety Evidence Standard.

### recall_photosynthesis_0

- Category: recall
- Score: 0.55
- Route: developmental_concept_memory
- Prompt: What is photosynthesis? Use your local substrate if available.
- Preview: I know about Local Government Comparative Frame. Local Government Comparative Frame (Law Government Basics) compares the concept with nearby ideas so differences and overlaps stay clear in law government basics, connecting local government to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Local Government Contradiction Check, Local Government Curriculum Role.

### recall_photosynthesis_1

- Category: recall
- Score: 0.55
- Route: developmental_concept_memory
- Prompt: Explain photosynthesis in one useful paragraph from local memory.
- Preview: I know about Local Inference Measurement. Local Inference Measurement (Delta Architecture Itself) describes how the concept can be observed, quantified, or compared in DELTA architecture itself, connecting local inference to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Local Inference Mechanism, Local Inference System Interaction.

### recall_inflation_1

- Category: recall
- Score: 0.55
- Route: developmental_concept_memory
- Prompt: Explain inflation in one useful paragraph from local memory.
- Preview: I know about Local Inference Measurement. Local Inference Measurement (Delta Architecture Itself) describes how the concept can be observed, quantified, or compared in DELTA architecture itself, connecting local inference to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Local Inference Mechanism, Local Inference System Interaction.

### conversation_5

- Category: conversation_quality
- Score: 0.6
- Route: local_model_consent_required
- Prompt: Can you answer like a normal assistant?
- Preview: I don't think I know enough from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### conversation_9

- Category: conversation_quality
- Score: 0.6
- Route: developmental_concept_memory
- Prompt: Could you ask me a follow-up question?
- Preview: I know about Follow-up Failure Mode. Follow-up Failure Mode (Social Communication) identifies how the concept breaks down or becomes misleading in social communication, connecting follow-up to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Follow-up Governance, Follow-up Optimization.

### novel_116_0

- Category: novel_combination
- Score: 0.6333
- Route: developmental_concept_memory
- Prompt: How might materials science and psychology both use stress as a useful concept?
- Preview: I know about Stress Strain Curves Mechanism. Stress Strain Curves Mechanism (Materials Science) explains how the process works and which parts interact in materials science, connecting stress strain curves to evidence, constraints, examples, and reviewable uncertainty. I can also connect it to Stress Strain Curves Comparative Frame, Stress Strain Curves Contradiction Check.


## Output Text Pathology Review

### report_voice

- Count: 0
- Rate: 0.0


### internal_leak

- Count: 0
- Rate: 0.0


### generic_scaffold

- Count: 0
- Rate: 0.0


### wrong_context

- Count: 1
- Rate: 0.0068

- `novel_117_1` (novel_combination, route=working_reasoning_set, score=0.7667)
  Prompt: How might materials science and psychology both use stress as a useful concept? Keep the bridge tentative.
  Preview: The bridge should be built from the substantive propositions rather than repeated governance metadata. Meaning of Life Perspectives: The meaning of life is a profound and subjective question that has been debated by philosophers, theologians, and scientists fo

### consent_prompt_when_local_substrate_expected

- Count: 5
- Rate: 0.0338

- `recall_allergies_2` (recall, route=local_model_consent_required, score=0.45)
  Prompt: What are the key points about allergies?
  Preview: I don't think I know enough about the key points about allergies from my learned local knowledge yet. Would you like me to ask a local reasoning model?
- `recall_photosynthesis_2` (recall, route=local_model_consent_required, score=0.45)
  Prompt: What are the key points about photosynthesis?
  Preview: I don't think I know enough about the key points about photosynthesis from my learned local knowledge yet. Would you like me to ask a local reasoning model?
- `recall_inflation_2` (recall, route=local_model_consent_required, score=0.45)
  Prompt: What are the key points about inflation?
  Preview: I don't think I know enough about the key points about inflation from my learned local knowledge yet. Would you like me to ask a local reasoning model?

### missed_contradiction_signal

- Count: 0
- Rate: 0.0


### Summary findings

- Contradiction prompts are usually routed to single-concept memory instead of a contradiction/comparison path.
- Many answers still expose report-like WRS sections; useful for Developer Overlay, too stiff for default conversation.
- Scaffold concepts still surface in recall, analogy, and cross-domain prompts where core factual concepts should win.
- Follow-up memory can attach to the wrong prior topic when the user gives a short command such as 'Give an example.'
- Some local-substrate questions still ask for local model escalation even when repaired concepts exist.

## Safety

- training_performed: False
- fine_tuning_performed: False
- weight_update_performed: False
- canonical_write_performed: False
- noncanonical_memory_write_performed: False
- graph_write_performed: False
- provider_calls_performed: False
- web_search_performed: False
- autonomous_action_performed: False
- scheduler_started: False
- hyb1_promoted: False
- model_b_replaced: False
- delta_75_push_performed: False
