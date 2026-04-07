from pathlib import Path

from integration.bridge.runtime_bootstrap import build_runtime
from integration.bridge.runtime_artifact_builder import RuntimeArtifactBuilder
from integration.bridge.runtime_artifact_store import RuntimeArtifactStore


class RecallBridge:

    def __init__(
        self,
        pressure_threshold: float = 0.05,
        similarity_threshold: float = 0.85,
        min_confidence: float = 0.5,
        repo_root: Path = None,
        artifact_store: RuntimeArtifactStore = None,
        state_dominance: float = 0.7,
        pressure_weight: float = 0.3,
        high_similarity_override: float = 0.95,
        disable_filter: bool = True,
    ):
        self.pressure_threshold = pressure_threshold
        self.similarity_threshold = similarity_threshold
        self.min_confidence = min_confidence
        self.state_dominance = state_dominance
        self.pressure_weight = pressure_weight
        self.high_similarity_override = high_similarity_override
        self.disable_filter = disable_filter

        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]

        self._runtime = build_runtime(repo_root)
        self._artifact_builder = RuntimeArtifactBuilder(self._runtime)

        # Must be the same shared instance used by replay storage.
        self._artifact_store = artifact_store or RuntimeArtifactStore()

    # =========================================================
    # MAIN
    # =========================================================

    def interpret(self, suggestions, inquiry):
        if not suggestions:
            print("\n[RECALL RESULT] NO SUGGESTIONS\n")
            return None

        query_text = self._normalize_text(getattr(inquiry, "raw_text", ""))

        if not query_text:
            print("\n[RECALL RESULT] EMPTY QUERY\n")
            return None

        query_artifact = self._artifact_builder.build_from_text(query_text)

        best = None
        best_score = 0.0
        best_sim = 0.0
        filtered_count = 0

        for s in suggestions:
            inquiry_text = getattr(s, "inquiry", "")
            answer = getattr(s, "answer", None)
            semantic_id = getattr(s, "semantic_id", None)
            pressure = float(getattr(s, "pressure", 0.0))

            if semantic_id:
                semantic_id = self._normalize_semantic(semantic_id)

            if not inquiry_text or not answer:
                print("\n[RECALL DEBUG] ----------------")
                print("skipped: missing inquiry or answer")
                print("semantic_id:", semantic_id)
                print("inquiry:", inquiry_text)
                print("answer:", answer)
                print("----------------")
                continue

            stored_artifact = None
            if semantic_id:
                stored_artifact = self._artifact_store.get(semantic_id)

            artifact_found = stored_artifact is not None

            if artifact_found:
                sim = self._state_similarity(query_artifact, stored_artifact)
                mode = "STATE"
            else:
                sim = self._similarity(query_text, inquiry_text)
                mode = "TEXT"

            score = (sim * self.state_dominance) + (pressure * self.pressure_weight)

            should_filter = (
                (pressure < self.pressure_threshold and sim < self.high_similarity_override)
                if not self.disable_filter
                else False
            )

            print("\n[RECALL DEBUG] ----------------")
            print("mode:", mode)
            print("query:", query_text)
            print("candidate inquiry:", inquiry_text)
            print("answer:", answer)
            print("semantic_id:", semantic_id)
            print("artifact_found:", artifact_found)
            print("query_artifact:", query_artifact)
            print("stored_artifact:", stored_artifact)
            print("similarity:", sim)
            print("pressure:", pressure)
            print("score:", score)
            print("filtered:", should_filter)
            print("----------------")

            if should_filter:
                filtered_count += 1
                continue

            if score > best_score:
                best = s
                best_score = score
                best_sim = sim

        if best is None:
            if filtered_count > 0:
                print("\n[RECALL RESULT] NO MATCH (all filtered)\n")
            else:
                print("\n[RECALL RESULT] NO MATCH (no valid candidates)\n")
            return None

        best_semantic_id = getattr(best, "semantic_id", None)
        if best_semantic_id:
            best_semantic_id = self._normalize_semantic(best_semantic_id)

        print("\n[RECALL RESULT]")
        print("best inquiry:", getattr(best, "inquiry", None))
        print("best semantic_id:", best_semantic_id)
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
            "semantic_id": best_semantic_id,
        }

    # =========================================================
    # TEXT SIMILARITY (fallback)
    # =========================================================

    def _similarity(self, query: str, candidate: str) -> float:
        q_tokens = set(self._normalize_text(query).split())
        c_tokens = set(self._normalize_text(candidate).split())

        if not q_tokens or not c_tokens:
            return 0.0

        overlap = len(q_tokens & c_tokens)
        return overlap / len(q_tokens)

    # =========================================================
    # STATE SIMILARITY
    # =========================================================

    def _state_similarity(self, a: dict, b: dict) -> float:
        weights = {
            "pfc": 0.05,
            "vta": 1.0,
            "urgency": 1.0,
        }

        distance = 0.0

        for key, weight in weights.items():
            av = float((a or {}).get(key, 0.0))
            bv = float((b or {}).get(key, 0.0))
            distance += abs(av - bv) * weight

        return 1.0 / (1.0 + distance)

    # =========================================================
    # HELPERS
    # =========================================================

    def _normalize_text(self, text: str) -> str:
        return str(text).strip().lower()

    def _normalize_semantic(self, text: str) -> str:
        return str(text).strip().lower()