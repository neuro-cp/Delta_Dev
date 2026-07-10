# RC2 Contradiction Engine

Created: 2026-07-10T06:25:56.628365+00:00
Cases: 20
Accuracy: 1.0
False-positive rate: 0.0
Missed direct contradiction rate: 0.0
Recommendation: MOVE_TO_ANALOGY_ENGINE_IF_FULL_BENCHMARK_PRESERVES_SYNTHESIS_AND_MEMORY

## Classification Metrics

- conditional_compatibility: 1.0
- definition_difference: 1.0
- direct_contradiction: 1.0
- insufficient_information: 1.0
- mutually_compatible: 1.0
- population_difference: 1.0
- scope_difference: 1.0
- timeframe_difference: 1.0
- unrelated_claims: 1.0

## Results

### PASS: direct_contradiction

- Prompt: Can these both be true: blood pressure is always constant, and blood pressure varies with activity and stress?
- Classification: direct_contradiction
- Confidence: 0.9
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: blood pressure is always constant Claim B: blood pressure varies with activity and stress?  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subjec

### PASS: direct_contradiction

- Prompt: Can these both be true: photosynthesis consumes stored glucose, and photosynthesis stores energy in sugars?
- Classification: direct_contradiction
- Confidence: 0.9
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: photosynthesis consumes stored glucose Claim B: photosynthesis stores energy in sugars?  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject. 

### PASS: direct_contradiction

- Prompt: Can these both be true: all allergies are harmless, and severe allergies can require emergency treatment?
- Classification: direct_contradiction
- Confidence: 0.9
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: all allergies are harmless Claim B: severe allergies can require emergency treatment?  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject.  C

### PASS: conditional_compatibility

- Prompt: Can these both be true: exercise raises blood pressure, and exercise lowers blood pressure?
- Classification: conditional_compatibility
- Confidence: 0.88
- Preview: Yes. They can both be true if they describe different conditions or timeframes.  Claim A: exercise raises blood pressure Claim B: exercise lowers blood pressure?  The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from another.  Classification: condit

### PASS: conditional_compatibility

- Prompt: Can these both be true: stress can raise blood pressure, and rest can lower blood pressure?
- Classification: conditional_compatibility
- Confidence: 0.88
- Preview: Yes. They can both be true if they describe different conditions or timeframes.  Claim A: stress can raise blood pressure Claim B: rest can lower blood pressure?  The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from another.  Classification: condit

### PASS: conditional_compatibility

- Prompt: Can these both be true: plants release oxygen, and plants consume oxygen during respiration?
- Classification: conditional_compatibility
- Confidence: 0.88
- Preview: Yes. They can both be true if they describe different conditions or timeframes.  Claim A: plants release oxygen Claim B: plants consume oxygen during respiration?  The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from another.  Classification: condi

### PASS: scope_difference

- Prompt: Can these both be true: allergies are immune reactions, and not every adverse drug reaction is an allergy?
- Classification: scope_difference
- Confidence: 0.84
- Preview: They are not necessarily contradictory; one claim is broader or narrower than the other.  Claim A: allergies are immune reactions Claim B: not every adverse drug reaction is an allergy?  The narrower claim can be true inside the broader category without defining the whole category.  Classification: scope difference.

### PASS: scope_difference

- Prompt: Can these both be true: all clinical evidence matters, and allergy evidence only matters for medication choices?
- Classification: scope_difference
- Confidence: 0.84
- Preview: They are not necessarily contradictory; one claim is broader or narrower than the other.  Claim A: all clinical evidence matters Claim B: allergy evidence only matters for medication choices?  The narrower claim can be true inside the broader category without defining the whole category.  Classification: scope differen

### PASS: timeframe_difference

- Prompt: Can these both be true: inflation is falling, and prices remain high shortly afterward?
- Classification: timeframe_difference
- Confidence: 0.82
- Preview: They are not necessarily contradictory; the likely difference is timeframe.  Claim A: inflation is falling Claim B: prices remain high shortly afterward?  One claim can describe a trend or cause, while the other describes a later or still-elevated state.  Classification: timeframe difference.

### PASS: timeframe_difference

- Prompt: Can these both be true: interest rates slow inflation, and inflation remains elevated shortly afterward?
- Classification: timeframe_difference
- Confidence: 0.82
- Preview: They are not necessarily contradictory; the likely difference is timeframe.  Claim A: interest rates slow inflation Claim B: inflation remains elevated shortly afterward?  One claim can describe a trend or cause, while the other describes a later or still-elevated state.  Classification: timeframe difference.

### PASS: population_difference

- Prompt: Can these both be true: this treatment helps adults, and this treatment does not help children?
- Classification: population_difference
- Confidence: 0.82
- Preview: They are not necessarily contradictory; they appear to describe different populations.  Claim A: this treatment helps adults Claim B: this treatment does not help children?  A claim about one population does not automatically transfer to a different population.  Classification: population difference.

### PASS: definition_difference

- Prompt: Can these both be true: memory means stored information, and working memory means active temporary processing?
- Classification: definition_difference
- Confidence: 0.82
- Preview: They may differ because the key term is being used in different ways.  Claim A: memory means stored information Claim B: working memory means active temporary processing?  The words overlap, but the definitions point to different levels of the concept.  Classification: definition difference.

### PASS: mutually_compatible

- Prompt: Can these both be true: blood pressure affects clinical interpretation, and allergies affect medication choice?
- Classification: mutually_compatible
- Confidence: 0.78
- Preview: I do not see a direct contradiction in those two claims.  Claim A: blood pressure affects clinical interpretation Claim B: allergies affect medication choice?  The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established.  Classification: mutually compatibl

### PASS: unrelated_claims

- Prompt: Can these both be true: gravity shapes orbital motion, and allergies involve immune responses?
- Classification: unrelated_claims
- Confidence: 0.66
- Preview: These do not look like a direct contradiction because they appear to discuss different subjects.  Claim A: gravity shapes orbital motion Claim B: allergies involve immune responses?  The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established.  Classificat

### PASS: insufficient_information

- Prompt: Does this evidence contradict the conclusion: the patient has symptoms, and the patient has a diagnosis?
- Classification: insufficient_information
- Confidence: 0.62
- Preview: I do not have enough information to decide whether those claims contradict each other.  Claim A: the patient has symptoms Claim B: the patient has a diagnosis?  The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established.  What would clarify it: - Whether 

### PASS: direct_contradiction

- Prompt: Check for contradiction: a patient has no medication allergies, and the same patient has a severe penicillin allergy?
- Classification: direct_contradiction
- Confidence: 0.9
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: a patient has no medication allergies Claim B: a patient has a severe penicillin allergy?  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject

### PASS: direct_contradiction

- Prompt: Are these statements contradictory: blood pressure varies with stress; blood pressure never changes with context.
- Classification: direct_contradiction
- Confidence: 0.9
- Preview: No. If these claims refer to the same subject, timeframe, and conditions, they conflict.  Claim A: blood pressure varies with stress Claim B: blood pressure never changes with context  The conflict comes from mutually exclusive wording, especially absolute or negative language, applied to the same apparent subject.  Cl

### PASS: conditional_compatibility

- Prompt: How can both be correct: regular exercise lowers resting blood pressure, and exercise raises blood pressure during activity?
- Classification: conditional_compatibility
- Confidence: 0.88
- Preview: Yes. They can both be true if they describe different conditions or timeframes.  Claim A: regular exercise lowers resting blood pressure Claim B: exercise raises blood pressure during activity?  The key is condition and timeframe: a short-term effect can differ from a long-term effect, or one condition can differ from 

### PASS: timeframe_difference

- Prompt: Can these both be true: inflation is falling, and prices are still higher than last year?
- Classification: timeframe_difference
- Confidence: 0.82
- Preview: They are not necessarily contradictory; the likely difference is timeframe.  Claim A: inflation is falling Claim B: prices are still higher than last year?  One claim can describe a trend or cause, while the other describes a later or still-elevated state.  Classification: timeframe difference.

### PASS: mutually_compatible

- Prompt: Can these both be true: allergies can constrain medication choices, and blood pressure supplies cardiovascular evidence?
- Classification: mutually_compatible
- Confidence: 0.78
- Preview: I do not see a direct contradiction in those two claims.  Claim A: allergies can constrain medication choices Claim B: blood pressure supplies cardiovascular evidence?  The claims need matching subject, predicate, timeframe, population, and condition before a contradiction can be established.  Classification: mutually 

## Safety

- training_performed: False
- fine_tuning_performed: False
- weight_update_performed: False
- canonical_write_performed: False
- noncanonical_memory_write_performed: False
- graph_write_performed: False
- replay_write_performed: False
- provider_calls_performed: False
- web_search_performed: False
- autonomous_action_performed: False
- scheduler_started: False
- hyb1_promoted: False
- model_b_replaced: False
