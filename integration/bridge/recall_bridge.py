class RecallBridge:
    """
    Converts semantic recall suggestions into a usable decision.

    Properties:
    - Pure interpreter (no mutation, no memory writes)
    - Uses similarity as primary selection signal
    - Uses pressure as secondary gating signal
    - Returns real stored answers when available
    """

    def __init__(
        self,
        pressure_threshold: float = 0.3,
        similarity_threshold: float = 0.3,
        min_confidence: float = 0.5,
    ):
        self.pressure_threshold = pressure_threshold
        self.similarity_threshold = similarity_threshold
        self.min_confidence = min_confidence

    def interpret(self, suggestions, inquiry):
        if not suggestions:
            return None

        query = inquiry.raw_text.lower()

        best = None
        best_score = 0.0

        # ---------------------------------
        # 1) Select best match via similarity + pressure
        # ---------------------------------
        for s in suggestions:
            semantic_id = str(getattr(s, "semantic_id", "")).lower()
            answer = getattr(s, "answer", None)

            if not semantic_id or not answer:
                continue

            sim = self._similarity(query, semantic_id, answer)
            pressure = float(getattr(s, "pressure", 0.0))

            score = sim * 0.8 + pressure * 0.2

            if score > best_score:
                best = s
                best_score = score

        # ---------------------------------
        # 2) Reject weak matches
        # ---------------------------------
        if best is None:
            return None

        semantic_id = str(getattr(best, "semantic_id", "")).lower()
        answer = getattr(best, "answer", None)
        pressure = float(getattr(best, "pressure", 0.0))

        sim = self._similarity(query, semantic_id, answer)

        if sim < self.similarity_threshold:
            return None

        if pressure < self.pressure_threshold:
            return None

        if not answer:
            return None

        # ---------------------------------
        # 3) Build response
        # ---------------------------------
        confidence = float(getattr(best, "confidence", best_score))
        confidence = max(self.min_confidence, min(1.0, confidence))

        return {
            "answer": answer,
            "confidence": confidence,
            "source": "recall",
            "semantic_id": getattr(best, "semantic_id", None),
        }

    # ---------------------------------
    # Helper: improved similarity
    # ---------------------------------
    def _similarity(self, query: str, semantic_id: str, answer: str) -> float:
        query = query.lower()
        semantic_id = semantic_id.lower()
        answer = (answer or "").lower()

        # ---------------------------------
        # 1. Semantic overlap (strong signal)
        # ---------------------------------
        if any(token in semantic_id for token in query.split()):
            return 0.8

        # ---------------------------------
        # 2. Answer-based fallback (CRITICAL)
        # allows "capital of germany" → "berlin"
        # ---------------------------------
        if any(token in query for token in answer.split()):
            return 0.6

        # ---------------------------------
        # 3. Token overlap fallback
        # ---------------------------------
        q_tokens = set(query.split())
        s_tokens = set(semantic_id.split())

        if not q_tokens or not s_tokens:
            return 0.0

        return len(q_tokens & s_tokens) / len(q_tokens)