class AnswerMemory:
    """
    Simple in-memory answer store.
    Fast recall layer (NOT semantic memory).

    Now supports:
    - exact match (priority)
    - fuzzy token overlap match (fallback)
    """

    def __init__(self):
        self._store = []

        # tuning knobs (safe defaults)
        self._fuzzy_threshold = 0.78
        self._min_tokens = 2

    def add(self, inquiry: str, answer: str, confidence: float):
        self._store.append({
            "inquiry": str(inquiry),
            "answer": str(answer),
            "confidence": float(confidence),
        })

    def lookup(self, inquiry: str):
        query = inquiry.strip().lower()

        # ---------------------------------
        # 1) EXACT MATCH (fast path)
        # ---------------------------------
        for item in reversed(self._store):
            if item["inquiry"].strip().lower() == query:
                return item

        # ---------------------------------
        # 2) FUZZY MATCH (token overlap)
        # ---------------------------------
        query_tokens = self._tokenize(query)

        if len(query_tokens) < self._min_tokens:
            return None

        best_item = None
        best_score = 0.0

        for item in reversed(self._store):
            stored = item["inquiry"].strip().lower()
            stored_tokens = self._tokenize(stored)

            if not stored_tokens:
                continue

            score = self._overlap_score(query_tokens, stored_tokens)

            if score > best_score:
                best_score = score
                best_item = item

        if best_score >= self._fuzzy_threshold:
            return best_item

        return None

    # =========================================
    # INTERNAL HELPERS
    # =========================================

    def _tokenize(self, text: str):
        return set(text.split())

    def _overlap_score(self, a_tokens, b_tokens):
        """
        Symmetric token overlap score.
        """
        intersection = len(a_tokens & b_tokens)
        if intersection == 0:
            return 0.0

        return intersection / max(len(a_tokens), len(b_tokens))