from integration.bridge.runtime_bootstrap import build_runtime
from integration.bridge.runtime_artifact_builder import RuntimeArtifactBuilder
from integration.bridge.runtime_artifact_store import RuntimeArtifactStore
from pathlib import Path


class RecallBridge:

    def __init__(
        self,
        pressure_threshold: float = 0.3,
        similarity_threshold: float = 0.85,
        min_confidence: float = 0.5,
        repo_root: Path = None,
    ):
        self.pressure_threshold = pressure_threshold
        self.similarity_threshold = similarity_threshold
        self.min_confidence = min_confidence

        # 🔴 runtime + artifact system
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]

        self._runtime = build_runtime(repo_root)
        self._artifact_builder = RuntimeArtifactBuilder(self._runtime)
        self._artifact_store = RuntimeArtifactStore()

    # =========================================================
    # MAIN
    # =========================================================

    def interpret(self, suggestions, inquiry):
        if not suggestions:
            return None

        query_text = inquiry.raw_text.lower().strip()

        # 🔴 build runtime state for query
        query_artifact = self._artifact_builder.build_from_text(query_text)

        best = None
        best_score = 0.0
        best_sim = 0.0

        for s in suggestions:
            inquiry_text = getattr(s, "inquiry", "")
            answer = getattr(s, "answer", None)
            semantic_id = getattr(s, "semantic_id", None)

            if not inquiry_text or not answer:
                continue

            pressure = float(getattr(s, "pressure", 0.0))

            # 🔴 enforce structural gating FIRST
            if pressure < self.pressure_threshold:
                continue

            # 🔴 try runtime artifact match
            stored_artifact = None
            if semantic_id:
                stored_artifact = self._artifact_store.get(semantic_id)

            if stored_artifact:
                sim = self._state_similarity(query_artifact, stored_artifact)
                mode = "STATE"
            else:
                sim = self._similarity(query_text, inquiry_text)
                mode = "TEXT"

            score = (sim * 0.7) + (pressure * 0.3)

            print("\n[RECALL DEBUG] ----------------")
            print("mode:", mode)
            print("query:", query_text)
            print("candidate inquiry:", inquiry_text)
            print("answer:", answer)
            print("similarity:", sim)
            print("pressure:", pressure)
            print("score:", score)

            if score > best_score:
                best = s
                best_score = score
                best_sim = sim

        if best is None:
            print("\n[RECALL RESULT] NO MATCH (all filtered)\n")
            return None

        print("\n[RECALL RESULT]")
        print("best inquiry:", getattr(best, "inquiry", None))
        print("best similarity:", best_sim)
        print("best score:", best_score)
        print("----------------\n")

        answer = getattr(best, "answer", None)
        confidence = float(getattr(best, "confidence", best_score))

        confidence = max(self.min_confidence, min(1.0, confidence))

        return {
            "answer": answer,
            "confidence": confidence,
            "source": "recall",
            "semantic_id": getattr(best, "semantic_id", None),
        }

    # =========================================================
    # TEXT SIMILARITY (fallback)
    # =========================================================

    def _similarity(self, query: str, candidate: str) -> float:
        q_tokens = set(query.split())
        c_tokens = set(candidate.lower().split())

        if not q_tokens or not c_tokens:
            return 0.0

        overlap = len(q_tokens & c_tokens)
        return overlap / len(q_tokens)

    # =========================================================
    # STATE SIMILARITY (new)
    # =========================================================

    def _state_similarity(self, a: dict, b: dict) -> float:
        score = 0.0

        for key in ["pfc", "vta", "urgency"]:
            av = float(a.get(key, 0.0))
            bv = float(b.get(key, 0.0))
            score += abs(av - bv)

        return 1.0 / (1.0 + score)