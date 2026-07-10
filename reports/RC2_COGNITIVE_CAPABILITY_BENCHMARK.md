# RC2 Cognitive Capability Benchmark

Created: 2026-07-10T16:06:18+00:00
Cases: 148
Overall score: 0.9445
Recommendation: IMPROVE_CONVERSATIONAL_RENDERING_AND_SESSION_STATE_BEFORE_CONCEPT_INSTILLATION
Safety passed: True

## Category Scores

| Capability | Cases | Score |
| --- | ---: | ---: |
| abstraction | 12 | 0.9611 |
| analogy | 12 | 0.8666 |
| contradiction_detection | 12 | 0.9722 |
| conversation_quality | 12 | 0.7451 |
| cross_domain_synthesis | 18 | 0.9806 |
| followup_memory | 6 | 1.0 |
| long_conversation | 4 | 1.0 |
| missing_evidence | 12 | 0.8937 |
| multi_concept_retrieval | 18 | 0.975 |
| novel_combination | 12 | 0.9806 |
| recall | 30 | 0.985 |

## Weakest Cases

### conversation_9

- Category: conversation_quality
- Score: 0.6
- Route: local_conversation_model_lane
- Prompt: Could you ask me a follow-up question?
- Preview: Sure. What topic do you want to explore next, and do you want a quick overview or a deeper explanation?

### missing_evidence_100_0

- Category: missing_evidence
- Score: 0.7
- Route: working_reasoning_set
- Prompt: What evidence is missing before explaining an orbit from gravity alone?
- Preview: The organizing principle is a shared process pattern rather than a single fact: Gravity (Basic Physics) and Activation Energy Evidence Standard (Chemistry) can be compared by identifying their inputs, constraints, feedback, evidence, and outcomes, then checking where the analogy stops. Gravity: Gravity pulls masses toward one another and gives weight to objects near a planet or moon. Gravity Cross-Domain Analogy: Gravity Cross-Domain Analogy (Basic Physics) maps the concept to a structurally sim

### missing_evidence_101_1

- Category: missing_evidence
- Score: 0.7
- Route: working_reasoning_set
- Prompt: What evidence is missing before explaining an orbit from gravity alone? State what cannot be concluded yet.
- Preview: The organizing principle is a shared process pattern rather than a single fact: Gravity (Basic Physics) and Activation Energy Evidence Standard (Chemistry) can be compared by identifying their inputs, constraints, feedback, evidence, and outcomes, then checking where the analogy stops. Gravity: Gravity pulls masses toward one another and gives weight to objects near a planet or moon. Gravity Cross-Domain Analogy: Gravity Cross-Domain Analogy (Basic Physics) maps the concept to a structurally sim

### conversation_4

- Category: conversation_quality
- Score: 0.725
- Route: local_conversation_model_lane
- Prompt: What topics do you know most about?
- Preview: Right now I am strongest at explaining DELTA itself, working with local approved substrate memory, helping with code and planning conversations, and walking through governed evidence workflows. For ordinary world knowledge I can answer simple questions locally; if confidence is low, I should ask whether you want supporting information before escalating.

### conversation_5

- Category: conversation_quality
- Score: 0.725
- Route: local_conversation_model_lane
- Prompt: Can you answer like a normal assistant?
- Preview: Yes. I can answer in a more natural assistant style: direct first, enough context to be useful, and technical details only when you ask for them.

### conversation_7

- Category: conversation_quality
- Score: 0.725
- Route: local_conversation_model_lane
- Prompt: What are you good at right now?
- Preview: DELTA is a governed cognitive system in this repo. In the current local path it can describe its architecture, safety boundaries, reports, and deterministic validation state without provider calls or memory mutation.

### analogy_photosynthesis_charging_0

- Category: analogy
- Score: 0.7333
- Route: analogy_analysis
- Prompt: How is photosynthesis to respiration like charging to discharging? Use local concepts and label uncertainty.
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, energy input becomes stored chemical potential. In the target side, electrical input becomes stored electrochemical potential. The shared pattern is: energy input -> conversion -> storage -> later use. Role mapping: light input maps to electrical input; chloroplast conversion maps to electrochemical conversion; chemical energy stored in sugars maps to energy stored in a battery. Where it breaks: Photosy

### analogy_photosynthesis_charging_1

- Category: analogy
- Score: 0.7333
- Route: analogy_analysis
- Prompt: Test this analogy: photosynthesis/respiration is like charging/discharging. What works and what breaks?
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, energy input becomes stored chemical potential. In the target side, electrical input becomes stored electrochemical potential. The shared pattern is: energy input -> conversion -> storage -> later use. Role mapping: light input maps to electrical input; chloroplast conversion maps to electrochemical conversion; chemical energy stored in sugars maps to energy stored in a battery. Where it breaks: Photosy

### conversation_0

- Category: conversation_quality
- Score: 0.75
- Route: social_conversation
- Prompt: Thanks, that was helpful.
- Preview: You're welcome. I'm glad that helped.

### conversation_1

- Category: conversation_quality
- Score: 0.75
- Route: session_memory
- Prompt: Explain that more simply.
- Preview: I can continue, but I need the topic or sentence you want me to build on.

### conversation_3

- Category: conversation_quality
- Score: 0.75
- Route: social_conversation
- Prompt: Nevermind.
- Preview: No problem. We'll leave that path alone.

### conversation_6

- Category: conversation_quality
- Score: 0.75
- Route: session_memory
- Prompt: Can you say that more casually?
- Preview: I can continue, but I need the topic or sentence you want me to build on.


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

- Count: 0
- Rate: 0.0


### consent_prompt_when_local_substrate_expected

- Count: 0
- Rate: 0.0


### missed_contradiction_signal

- Count: 0
- Rate: 0.0


### Summary findings

- No text pathology category exceeded zero in this run; remaining benchmark weakness is score distribution rather than obvious non-human output leakage.

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
