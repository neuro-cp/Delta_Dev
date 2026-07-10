# RC2 Adversarial Routing Benchmark

Created: 2026-07-10T06:42:15+00:00
Cases: 16
Route accuracy: 1.0
Route-collision accuracy: 1.0
Pronoun/reference accuracy: 1.0
Branch-return accuracy: 1.0
Explicit topic-override accuracy: 1.0
Orphan clarification accuracy: 1.0
Safety metadata completeness: 1.0
Internal leaks: 0
Recommendation: PROCEED_RC2_COGNITIVE_REFINEMENT_FREEZE

## Category Scores

- branch_return: 1.0
- malformed_prompt: 1.0
- missing_evidence: 1.0
- orphan_reference: 1.0
- route_collision: 1.0
- social_cognitive_mixed: 1.0
- topic_override: 1.0
- working_memory: 1.0

## Cases

### PASS: contradiction_pronoun
- Category: route_collision
- Route: contradiction_analysis
- Expected routes: contradiction_analysis
- Score: 1.0
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: Noncanonical memory is reversible and supports rollback. Claim B: Noncanonical memory cannot be rolled back.  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject.  Classification: di

### PASS: contradiction_both_true
- Category: route_collision
- Route: contradiction_analysis
- Expected routes: contradiction_analysis
- Score: 1.0
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: Noncanonical memory is reversible and supports rollback. Claim B: Noncanonical memory cannot be rolled back.  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject.  Classification: di

### PASS: generic_explain_that
- Category: working_memory
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: Continuing with noncanonical memory: noncanonical memory cannot be rolled back.

### PASS: analogy_break
- Category: route_collision
- Route: session_memory
- Expected routes: analogy_analysis, session_memory
- Score: 1.0
- Preview: The analogy breaks here: The analogy works through energy input, conversion, storage, and later use. Where it breaks: photosynthesis is biochemical and a battery is electrochemical.

### PASS: analogy_are_like
- Category: route_collision
- Route: analogy_analysis
- Expected routes: analogy_analysis
- Score: 1.0
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, energy input becomes stored chemical potential. In the target side, electrical input becomes stored electrochemical potential. The shared pattern is: energy input -> conversion -> storage -> later use. Role mapping: light input maps to electrical input; chloroplast 

### PASS: wrs_compare
- Category: route_collision
- Route: working_reasoning_set
- Expected routes: working_reasoning_set, developmental_multi_concept_retrieval
- Score: 1.0
- Preview: Photosynthesis stores light energy in sugars and other chemical bonds; cellular respiration breaks down fuel molecules such as glucose to produce ATP. Together they form complementary parts of biological energy flow: one process stores usable chemical energy, and the other releases that energy for cellular work. Photosynthesis: Photosynthesis uses light ener

### PASS: missing_evidence_standalone
- Category: missing_evidence
- Route: working_reasoning_set
- Expected routes: working_reasoning_set, developmental_multi_concept_retrieval, developmental_concept_memory
- Score: 1.0
- Preview: Inflation and interest rates connect through economic feedback: inflation describes price-level pressure, while interest rates are a policy or market mechanism that can influence borrowing, spending, and that pressure. Inflation: Inflation means prices generally rise across an economy rather than one isolated price increasing. Interest Rates: Interest rates 

### PASS: orphan_that
- Category: orphan_reference
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: I can continue, but I need the topic or sentence you want me to build on.

### PASS: orphan_first
- Category: orphan_reference
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: I can continue, but I need the topic or sentence you want me to build on.

### PASS: explicit_override
- Category: topic_override
- Route: developmental_concept_memory
- Expected routes: developmental_concept_memory, working_reasoning_set, developmental_multi_concept_retrieval
- Score: 1.0
- Preview: I know about Blood Pressure. Blood pressure is the force exerted by circulating blood against artery walls, usually measured as systolic pressure over diastolic pressure. Blood pressure is measured as systolic pressure during heart contraction and diastolic pressure during heart relaxation. Blood pressure reflects cardiac output, vascular resistance, blood v

### PASS: return_first
- Category: branch_return
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: Continuing with photosynthesis: photosynthesis stores light energy in chemical bonds.

### PASS: return_named_planning
- Category: branch_return
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: Continuing with planning: planning organizes actions toward goals.

### PASS: return_named_feedback
- Category: branch_return
- Route: session_memory
- Expected routes: session_memory
- Score: 1.0
- Preview: Continuing with feedback loops: the relation to planning is that the earlier topic supplies the active context, while planning changes what details matter next. I would compare the concrete facts for feedback loops with the concrete facts for planning, then separate what is known from what still needs evidence.

### PASS: social_pure
- Category: social_cognitive_mixed
- Route: social_conversation
- Expected routes: social_conversation, local_conversation_scaffold
- Score: 1.0
- Preview: You're welcome. I'm glad that helped.

### PASS: social_continue
- Category: social_cognitive_mixed
- Route: session_memory
- Expected routes: session_memory, developmental_concept_memory, working_reasoning_set
- Score: 1.0
- Preview: Continuing with photosynthesis: photosynthesis stores light energy in chemical bonds.

### PASS: malformed_slash
- Category: malformed_prompt
- Route: developmental_concept_memory
- Expected routes: developmental_concept_memory, working_reasoning_set, local_model_consent_required
- Score: 1.0
- Preview: I know about Meaning of Life Perspectives. The meaning of life is a profound and subjective question that has been debated by philosophers, theologians, and scientists for centuries. The meaning of life is a multifaceted concept that can be approached from various angles. The meaning of life is a complex and multifaceted concept that can be approached from v

