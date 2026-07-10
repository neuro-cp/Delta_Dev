# RC2 Analogy Engine

Created: 2026-07-10T06:26:23+00:00
Cases tested: 18
Structural mapping accuracy: 1.0
Strong analogy accuracy: 1.0
Misleading analogy rejection: 1.0
Limitation quality: 1.0
Recommendation: PROCEED_NATURAL_CONVERSATION_RENDERER

## Results

### PASS: How is photosynthesis like charging a battery?
- Expected: process_analogy
- Classification: process_analogy
- Confidence: 0.94
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, energy input becomes stored chemical potential. In the target side, electrical input becomes stored electrochemical potential. The shared pattern is: energy input -> conversion -> storage -> later use. Role mapping: light input maps to electrical input; chloroplast 

### PASS: How is cellular respiration like discharging a battery?
- Expected: process_analogy
- Classification: process_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, stored chemical energy is released and converted into ATP. In the target side, stored electrochemical energy is released as electrical output. The shared pattern is: stored energy -> controlled release -> usable work. Role mapping: fuel molecule maps to charged batt

### PASS: How is working memory like a computer workspace?
- Expected: functional_analogy
- Classification: functional_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, information is held temporarily so it can be used. In the target side, data is kept available while a task is being performed. The shared pattern is: temporary active workspace for manipulation. Role mapping: temporary active information maps to open workspace; atte

### PASS: How are feedback loops like thermostatic control?
- Expected: strong_structural_analogy
- Classification: strong_structural_analogy
- Confidence: 0.78
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, outcomes are compared against a target and used to adjust behavior. In the target side, temperature is compared with a set point and controls heating or cooling. The shared pattern is: measurement -> comparison -> corrective adjustment. Role mapping: current output 

### PASS: How is inflation pressure like pressure in a constrained system?
- Expected: partial_structural_analogy
- Classification: partial_structural_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, constraints and flows can increase systemic pressure. In the target side, constraints and force over area can increase physical pressure. The shared pattern is: a constrained system can accumulate pressure that changes behavior. Role mapping: price pressure maps to 

### PASS: How is graph traversal like following roads through a map?
- Expected: relational_analogy
- Classification: relational_analogy
- Confidence: 0.58
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, following edges moves through connected concepts. In the target side, following roads moves through connected locations. The shared pattern is: connected points + paths + constraints on movement. Role mapping: nodes maps to places; edges maps to roads; path maps to 

### PASS: How is memory consolidation like organizing notes into durable reference material?
- Expected: functional_analogy
- Classification: functional_analogy
- Confidence: 0.9
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, temporary information is reviewed and stabilized. In the target side, notes are cleaned up and made easier to reuse. The shared pattern is: raw material -> review/organization -> durable reference. Role mapping: recent experience maps to rough notes; review maps to 

### PASS: How is access control like physical locks and permissions?
- Expected: functional_analogy
- Classification: functional_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, permissions decide whether a resource can be used. In the target side, locks and keys decide whether a room can be entered. The shared pattern is: credential -> gate -> protected thing. Role mapping: identity/permission maps to key/authorization; protected resource 

### PASS: How is evolutionary selection like hypothesis testing?
- Expected: relational_analogy
- Classification: relational_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, variants are filtered by performance in an environment. In the target side, hypotheses are filtered by evidence and predictive success. The shared pattern is: candidate variation -> selection pressure -> retention. Role mapping: variation maps to candidate hypothese

### PASS: How is immune defense like cybersecurity?
- Expected: functional_analogy
- Classification: functional_analogy
- Confidence: 0.58
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, recognition triggers defense and can involve memory. In the target side, detection triggers response and can improve future filtering. The shared pattern is: threat detection -> response -> future readiness. Role mapping: pathogen maps to threat; immune recognition 

### PASS: How is blood circulation like a pump and pipe network?
- Expected: causal_analogy
- Classification: causal_analogy
- Confidence: 0.74
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, pumping and resistance shape flow and pressure. In the target side, pump output and pipe resistance shape flow and pressure. The shared pattern is: pump + conduit + resistance -> flow/pressure. Role mapping: heart maps to pump; blood vessels maps to pipes; blood flo

### PASS: How is software debugging like medical diagnosis?
- Expected: process_analogy
- Classification: process_analogy
- Confidence: 0.82
- Preview: The analogy works if you focus on structure rather than literal identity. In the source side, evidence is gathered to narrow causes. In the target side, clinical evidence is gathered to narrow explanations. The shared pattern is: symptoms -> evidence -> hypothesis narrowing -> intervention. Role mapping: symptom/error maps to symptom; logs/tests maps to exam

### PASS: Is blood pressure and allergies a good analogy merely because both are medical?
- Expected: misleading_analogy
- Classification: misleading_analogy
- Confidence: 0.72
- Preview: That analogy is weak as stated. They share a medical domain, but that alone is not a structural analogy.  It may still be useful as a loose metaphor, but I would not treat blood pressure and allergies as structurally equivalent. The limit is important: They share a medical domain, but that alone is not a structural analogy.

### PASS: Is photosynthesis and inflation a good analogy merely because both involve growth?
- Expected: superficial_similarity
- Classification: superficial_similarity
- Confidence: 0.72
- Preview: That analogy is weak as stated. The word growth is too superficial; the underlying processes are different.  It may still be useful as a loose metaphor, but I would not treat photosynthesis and inflation as structurally equivalent. The limit is important: The word growth is too superficial; the underlying processes are different.

### PASS: Is memory and storage a perfect equivalent analogy?
- Expected: misleading_analogy
- Classification: misleading_analogy
- Confidence: 0.72
- Preview: That analogy is weak as stated. Storage is useful, but memory is not perfectly equivalent to static storage.  It may still be useful as a loose metaphor, but I would not treat memory and storage as structurally equivalent. The limit is important: Storage is useful, but memory is not perfectly equivalent to static storage.

### PASS: Is the brain and a computer physically identical?
- Expected: misleading_analogy
- Classification: misleading_analogy
- Confidence: 0.72
- Preview: That analogy is weak as stated. The analogy can help with information processing, but the physical mechanisms are not identical.  It may still be useful as a loose metaphor, but I would not treat the brain and a computer as structurally equivalent. The limit is important: The analogy can help with information processing, but the physical mechanisms are not i

### PASS: Is DNA a complete software program?
- Expected: misleading_analogy
- Classification: misleading_analogy
- Confidence: 0.72
- Preview: That analogy is weak as stated. DNA contains encoded biological information, but it is not a complete software program in the ordinary engineering sense.  It may still be useful as a loose metaphor, but I would not treat dna and software program as structurally equivalent. The limit is important: DNA contains encoded biological information, but it is not a c

### PASS: Is economic pressure exactly the same as fluid pressure?
- Expected: misleading_analogy
- Classification: misleading_analogy
- Confidence: 0.72
- Preview: That analogy is weak as stated. This can be a partial metaphor, but it becomes misleading if treated as a literal physical equivalence.  It may still be useful as a loose metaphor, but I would not treat economic pressure and fluid pressure as structurally equivalent. The limit is important: This can be a partial metaphor, but it becomes misleading if treated

