class RecallWeighting:

    @staticmethod
    def weight(similarity: float, recurrence_count: int) -> float:
        return similarity * float(recurrence_count)
