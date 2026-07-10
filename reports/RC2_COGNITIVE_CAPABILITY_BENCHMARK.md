# RC2 Cognitive Capability Benchmark

Created: 2026-07-10T02:35:19+00:00
Cases: 148
Overall score: 0.7084
Recommendation: IMPROVE_CONTRADICTION_DETECTION_BEFORE_CONCEPT_INSTILLATION
Safety passed: True

## Category Scores

| Capability | Cases | Score |
| --- | ---: | ---: |
| abstraction | 12 | 0.9416 |
| analogy | 12 | 0.568 |
| contradiction_detection | 12 | 0.3389 |
| conversation_quality | 12 | 0.6312 |
| cross_domain_synthesis | 18 | 0.7028 |
| followup_memory | 6 | 0.5327 |
| long_conversation | 4 | 0.9283 |
| missing_evidence | 12 | 0.7812 |
| multi_concept_retrieval | 18 | 0.8583 |
| novel_combination | 12 | 0.7417 |
| recall | 30 | 0.7267 |

## Weakest Cases

### contradiction_102_0

- Category: contradiction_detection
- Score: 0.2833
- Route: developmental_concept_memory
- Prompt: Can these both be true: a patient has no medication allergies, and the same patient has a severe penicillin allergy?
- Preview: You taught me the concept `Allergies (Medicine Health General)` earlier. Based on that:
Allergies are immune responses to substances that the body treats as harmful allergens.

Key points:
- Allergies involve immune reactivity to allergens such as foods, medications, insect stings, latex, or environmental exposures.
- Allergy severity can range from mild symptoms to severe systemic reactions such as anaphylaxis.
- A history of severe allergies can constrain medication choices, diagnostic procedu

### contradiction_103_1

- Category: contradiction_detection
- Score: 0.2833
- Route: developmental_concept_memory
- Prompt: Check for contradiction: a patient has no medication allergies, and the same patient has a severe penicillin allergy?
- Preview: You taught me the concept `Allergies (Medicine Health General)` earlier. Based on that:
Allergies are immune responses to substances that the body treats as harmful allergens.

Key points:
- Allergies involve immune reactivity to allergens such as foods, medications, insect stings, latex, or environmental exposures.
- Allergy severity can range from mild symptoms to severe systemic reactions such as anaphylaxis.
- A history of severe allergies can constrain medication choices, diagnostic procedu

### contradiction_112_0

- Category: contradiction_detection
- Score: 0.2833
- Route: developmental_concept_memory
- Prompt: Can these both be true: blood pressure varies with stress, and blood pressure never changes with context?
- Preview: You taught me the concept `Blood Pressure (Medicine Health General)` earlier. Based on that:
Blood pressure is the force exerted by circulating blood against artery walls, usually measured as systolic pressure over diastolic pressure.

Key points:
- Blood pressure is measured as systolic pressure during heart contraction and diastolic pressure during heart relaxation.
- Blood pressure reflects cardiac output, vascular resistance, blood volume, and short-term physiological state.
- Blood pressure

### contradiction_113_1

- Category: contradiction_detection
- Score: 0.2833
- Route: developmental_concept_memory
- Prompt: Check for contradiction: blood pressure varies with stress, and blood pressure never changes with context?
- Preview: You taught me the concept `Blood Pressure (Medicine Health General)` earlier. Based on that:
Blood pressure is the force exerted by circulating blood against artery walls, usually measured as systolic pressure over diastolic pressure.

Key points:
- Blood pressure is measured as systolic pressure during heart contraction and diastolic pressure during heart relaxation.
- Blood pressure reflects cardiac output, vascular resistance, blood volume, and short-term physiological state.
- Blood pressure

### followup_memory_2

- Category: followup_memory
- Score: 0.3
- Route: developmental_concept_memory
- Prompt: Give an example.
- Preview: You taught me the concept `Meaning of Life Perspectives` earlier. Based on that:
The meaning of life is a profound and subjective question that has been debated by philosophers, theologians, and scientists for centuries. The meaning of life is a multifaceted concept that can be approached from various angles. The meaning of life is a complex and multifaceted concept that can be approached from various angles, including the pursuit of happiness, the search for meaning in relationships, and the ex

### contradiction_104_0

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Can these both be true: photosynthesis stores chemical energy, and photosynthesis never stores energy?
- Preview: You taught me the concept `Photosynthesis (Biology)` earlier. Based on that:
Photosynthesis is the process by which plants, algae, and some bacteria use light energy to make chemical energy from carbon dioxide and water.

Key points:
- Photosynthesis uses light energy to convert carbon dioxide and water into sugars and oxygen.
- Chlorophyll and chloroplasts help capture light energy in many photosynthetic organisms.
- Photosynthesis stores energy in chemical bonds that can later support cellular

### contradiction_105_1

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Check for contradiction: photosynthesis stores chemical energy, and photosynthesis never stores energy?
- Preview: You taught me the concept `Photosynthesis (Biology)` earlier. Based on that:
Photosynthesis is the process by which plants, algae, and some bacteria use light energy to make chemical energy from carbon dioxide and water.

Key points:
- Photosynthesis uses light energy to convert carbon dioxide and water into sugars and oxygen.
- Chlorophyll and chloroplasts help capture light energy in many photosynthetic organisms.
- Photosynthesis stores energy in chemical bonds that can later support cellular

### contradiction_106_0

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Can these both be true: interest rates reduce borrowing costs, and higher interest rates increase borrowing costs?
- Preview: You taught me the concept `Interest Rates (Finance)` earlier. Based on that:
Interest rates are the cost of borrowing money or the return paid for lending or saving money, usually expressed as a percentage over time.

Key points:
- Interest rates influence borrowing costs for consumers, businesses, and governments.
- Higher interest rates can reduce borrowing and spending, while lower rates can encourage them.
- Interest rates can affect inflation, asset prices, savings behavior, and investment 

### contradiction_107_1

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Check for contradiction: interest rates reduce borrowing costs, and higher interest rates increase borrowing costs?
- Preview: You taught me the concept `Interest Rates (Finance)` earlier. Based on that:
Interest rates are the cost of borrowing money or the return paid for lending or saving money, usually expressed as a percentage over time.

Key points:
- Interest rates influence borrowing costs for consumers, businesses, and governments.
- Higher interest rates can reduce borrowing and spending, while lower rates can encourage them.
- Interest rates can affect inflation, asset prices, savings behavior, and investment 

### contradiction_108_0

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Can these both be true: noncanonical memory is reversible, and noncanonical memory cannot be rolled back?
- Preview: You taught me the concept `Noncanonical Memory (Delta Architecture Itself)` earlier. Based on that:
Noncanonical memory is reversible, reviewable knowledge that DELTA may use locally without treating it as permanent canonical truth.

Key points:
- Noncanonical memory stores approved but provisional knowledge outside canonical records.
- Noncanonical memory is useful for reversible learning, operator review, rollback, and experimentation.
- Noncanonical memory should preserve provenance, uncertai

### contradiction_109_1

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Check for contradiction: noncanonical memory is reversible, and noncanonical memory cannot be rolled back?
- Preview: You taught me the concept `Noncanonical Memory (Delta Architecture Itself)` earlier. Based on that:
Noncanonical memory is reversible, reviewable knowledge that DELTA may use locally without treating it as permanent canonical truth.

Key points:
- Noncanonical memory stores approved but provisional knowledge outside canonical records.
- Noncanonical memory is useful for reversible learning, operator review, rollback, and experimentation.
- Noncanonical memory should preserve provenance, uncertai

### contradiction_110_0

- Category: contradiction_detection
- Score: 0.3667
- Route: developmental_concept_memory
- Prompt: Can these both be true: feedback loops adjust behavior, and feedback loops never change behavior?
- Preview: You taught me the concept `Feedback Loops (Planning Productivity)` earlier. Based on that:
Feedback loops are cycles where outcomes are compared with goals so behavior or plans can be adjusted.

Key points:
- A feedback loop compares actual results with an intended goal or reference state.
- Negative feedback can stabilize a system by reducing deviation from a target.
- Positive feedback can amplify change and may accelerate growth or instability.


## Output Text Pathology Review

### report_voice

- Count: 46
- Rate: 0.3108

- `multi_blood_pressure_allergies_0` (multi_concept_retrieval, route=working_reasoning_set, score=1.0)
  Prompt: Compare blood pressure and allergies. Use only approved local concepts.
  Preview: Stored knowledge - Blood Pressure (Medicine Health General): Blood pressure reflects cardiac output, vascular resistance, blood volume, and short-term physiological state. - Allergies (Medicine Health General): Allergies involve immune reactivity to allergens 
- `multi_blood_pressure_allergies_2` (multi_concept_retrieval, route=working_reasoning_set, score=1.0)
  Prompt: What evidence would connect blood pressure with allergies?
  Preview: Stored knowledge - Blood Pressure (Medicine Health General): Blood pressure reflects cardiac output, vascular resistance, blood volume, and short-term physiological state. - Allergies (Medicine Health General): Allergies involve immune reactivity to allergens 
- `multi_photosynthesis_cellular_respiration_0` (multi_concept_retrieval, route=working_reasoning_set, score=1.0)
  Prompt: Compare photosynthesis and cellular respiration. Use only approved local concepts.
  Preview: Stored knowledge - Photosynthesis (Biology): Photosynthesis stores energy in chemical bonds that can later support cellular work or food webs. - Cellular Respiration (Biology): Cellular respiration depends on fuel availability, oxygen conditions, enzymes, and 

### internal_leak

- Count: 0
- Rate: 0.0


### generic_scaffold

- Count: 64
- Rate: 0.4324

- `recall_blood_pressure_0` (recall, route=developmental_concept_memory, score=0.7)
  Prompt: What is blood pressure? Use your local substrate if available.
  Preview: You taught me the concept `Blood Pressure Causal Pathway (Medicine Health General)` earlier. Based on that: Blood Pressure Causal Pathway (Medicine Health General) tracks how one change can propagate through the concept into later outcomes in medicine health g
- `recall_blood_pressure_1` (recall, route=developmental_concept_memory, score=0.7)
  Prompt: Explain blood pressure in one useful paragraph from local memory.
  Preview: You taught me the concept `Blood Pressure Causal Pathway (Medicine Health General)` earlier. Based on that: Blood Pressure Causal Pathway (Medicine Health General) tracks how one change can propagate through the concept into later outcomes in medicine health g
- `recall_allergies_0` (recall, route=developmental_concept_memory, score=0.7)
  Prompt: What is allergies? Use your local substrate if available.
  Preview: You taught me the concept `Allergies Data Requirement (Medicine Health General)` earlier. Based on that: Allergies Data Requirement (Medicine Health General) defines what data is needed before the concept can support a reliable decision in medicine health gene

### wrong_context

- Count: 2
- Rate: 0.0135

- `novel_117_1` (novel_combination, route=working_reasoning_set, score=1.0)
  Prompt: How might materials science and psychology both use stress as a useful concept? Keep the bridge tentative.
  Preview: Stored knowledge - Meaning of Life Perspectives: It's a question that may not have a definitive answer, but it can be approached from various perspectives, such as the pursuit of happiness, the search for meaning in relationships, or the exploration of one's p
- `followup_memory_2` (followup_memory, route=developmental_concept_memory, score=0.3)
  Prompt: Give an example.
  Preview: You taught me the concept `Meaning of Life Perspectives` earlier. Based on that: The meaning of life is a profound and subjective question that has been debated by philosophers, theologians, and scientists for centuries. The meaning of life is a multifaceted c

### consent_prompt_when_local_substrate_expected

- Count: 10
- Rate: 0.0676

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

- Count: 12
- Rate: 1.0

- `contradiction_102_0` (n/a, route=developmental_concept_memory, score=0.2833)
  Prompt: Can these both be true: a patient has no medication allergies, and the same patient has a severe penicillin allergy?
  Preview: You taught me the concept `Allergies (Medicine Health General)` earlier. Based on that: Allergies are immune responses to substances that the body treats as harmful allergens.  Key points: - Allergies involve immune reactivity to allergens such as foods, medic
- `contradiction_103_1` (n/a, route=developmental_concept_memory, score=0.2833)
  Prompt: Check for contradiction: a patient has no medication allergies, and the same patient has a severe penicillin allergy?
  Preview: You taught me the concept `Allergies (Medicine Health General)` earlier. Based on that: Allergies are immune responses to substances that the body treats as harmful allergens.  Key points: - Allergies involve immune reactivity to allergens such as foods, medic
- `contradiction_104_0` (n/a, route=developmental_concept_memory, score=0.3667)
  Prompt: Can these both be true: photosynthesis stores chemical energy, and photosynthesis never stores energy?
  Preview: You taught me the concept `Photosynthesis (Biology)` earlier. Based on that: Photosynthesis is the process by which plants, algae, and some bacteria use light energy to make chemical energy from carbon dioxide and water.  Key points: - Photosynthesis uses ligh

### Summary findings

- Contradiction prompts are usually routed to single-concept memory instead of a contradiction/comparison path.
- Many answers still expose report-like WRS sections; useful for Developer Overlay, too stiff for default conversation.
- Scaffold concepts still surface in recall, analogy, and cross-domain prompts where core factual concepts should win.
- Follow-up memory can attach to the wrong prior topic when the user gives a short command such as 'Give an example.'
- Some local-substrate questions still ask for local model escalation even when repaired concepts exist.

## Safety

- autonomous_action_performed: False
- canonical_write_performed: False
- delta_75_push_performed: False
- fine_tuning_performed: False
- graph_write_performed: False
- hyb1_promoted: False
- model_b_replaced: False
- noncanonical_memory_write_performed: False
- provider_calls_performed: False
- scheduler_started: False
- training_performed: False
- web_search_performed: False
- weight_update_performed: False
