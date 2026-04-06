class AnswerMemory:
    """
    Simple in-memory answer store.
    This is the fast recall layer (NOT semantic memory).
    """

    def __init__(self):
        self._store = []

    def add(self, inquiry: str, answer: str, confidence: float):
        self._store.append({
            "inquiry": inquiry,
            "answer": answer,
            "confidence": confidence,
        })

    def lookup(self, inquiry: str):
        for item in reversed(self._store):
            if item["inquiry"].strip().lower() == inquiry.strip().lower():
                return item
        return None
