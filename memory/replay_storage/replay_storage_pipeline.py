from __future__ import annotations

from types import SimpleNamespace
from typing import Any, List


class ReplayStoragePipeline:
    """
    Replay-local semantic extraction pipeline.

    Contract:
    - May be constructed with a replay_id
    - Accepts a sequence of bundle-like or proposal-like objects
    - Produces replay-local semantic records
    - Never executes work at import time
    - Stays tolerant to partial/in-progress bundle schemas
    """

    def __init__(self, replay_id: str | None = None):
        self.replay_id = replay_id or "replay_local"

    # =========================================================
    # MAIN ENTRY
    # =========================================================

    def run(self, bundles) -> list[dict]:
        print("\n[DEBUG] ===== REPLAY PIPELINE START =====")
        print(f"[DEBUG] replay_id = {self.replay_id}")
        print(f"[DEBUG] bundles received = {0 if not bundles else len(bundles)}")

        if not bundles:
            print("[DEBUG] no bundles provided")
            print("[DEBUG] ===== REPLAY PIPELINE END =====\n")
            return []

        proposals = self._extract_proposals(bundles)

        print(f"[DEBUG] proposals (raw) = {len(proposals)}")

        if not proposals:
            print("[DEBUG] injecting synthetic proposals")
            proposals = self._inject_synthetic_proposals(bundles)

        print(f"[DEBUG] proposals (final) = {len(proposals)}")

        applied = self._build_semantic_records(proposals)

        print(f"[DEBUG] applied deltas = {len(applied)}")
        if applied:
            print(f"[DEBUG] sample applied = {applied[0]}")

        print("[DEBUG] ===== REPLAY PIPELINE END =====\n")
        return applied

    # =========================================================
    # PROPOSAL EXTRACTION
    # =========================================================

    def _extract_proposals(self, bundles) -> list[Any]:
        proposals: list[Any] = []

        for bundle in bundles:
            if bundle is None:
                continue

            # Case 1: bundle already is proposal-like
            if hasattr(bundle, "source_bundle") or hasattr(bundle, "deltas"):
                proposals.append(bundle)
                continue

            # Case 2: bundle has .proposals
            bundle_proposals = getattr(bundle, "proposals", None)
            if bundle_proposals:
                proposals.extend(bundle_proposals)
                continue

            # Case 3: dict bundle with proposals
            if isinstance(bundle, dict):
                dict_proposals = bundle.get("proposals")
                if dict_proposals:
                    proposals.extend(dict_proposals)

        return proposals

    def _inject_synthetic_proposals(self, bundles) -> list[Any]:
        synthetic = []

        for bundle in bundles:
            source_bundle = self._coerce_source_bundle(bundle)

            answer = getattr(source_bundle, "answer", None)
            if not answer:
                continue

            inquiry_text = getattr(source_bundle, "inquiry", "") or ""
            delta_key = self._stable_key(inquiry_text, answer)

            proposal = SimpleNamespace(
                source_bundle=source_bundle,
                deltas=[
                    SimpleNamespace(
                        target=f"synthetic:{delta_key}",
                        delta_type="synthetic",
                    )
                ],
                bounded=True,
                replay_consistent=True,
                proposal_id=f"proposal:{delta_key}",
            )
            synthetic.append(proposal)

        return synthetic

    # =========================================================
    # RECORD BUILDING
    # =========================================================

    def _build_semantic_records(self, proposals) -> list[dict]:
        applied: list[dict] = []

        for proposal in proposals:
            source_bundle = getattr(proposal, "source_bundle", None)
            if source_bundle is None:
                continue

            answer = getattr(source_bundle, "answer", None)
            confidence = getattr(source_bundle, "confidence", None)
            inquiry_text = getattr(source_bundle, "inquiry", "") or ""

            if not answer:
                continue

            deltas = getattr(proposal, "deltas", None) or []
            if not deltas:
                deltas = [
                    SimpleNamespace(
                        target=f"synthetic:{self._stable_key(inquiry_text, answer)}",
                        delta_type="synthetic",
                    )
                ]

            for delta in deltas:
                combined = self._build_semantic_text(inquiry_text, answer)

                print("\n[SEMANTIC BUILD] ----------------")
                print("inquiry_text:", inquiry_text)
                print("answer:", answer)
                print("combined_raw:", f"{inquiry_text} {answer}".strip())
                print("combined_normalized:", combined)
                print("--------------------------------\n")

                applied.append(
                    {
                        "semantic_id": f"sem:{combined}",
                        "pattern_type": getattr(delta, "delta_type", "unknown"),
                        "supporting_episode_ids": [self.replay_id],
                        "recurrence_count": 1,
                        "persistence_span": 1,
                        "stability_classification": "unstable",
                        "inquiry": inquiry_text,
                        "answer": answer,
                        "confidence": self._safe_confidence(confidence),
                        "source_replay_id": self.replay_id,
                    }
                )

        return applied

    # =========================================================
    # BUNDLE COERCION
    # =========================================================

    def _coerce_source_bundle(self, bundle):
        if bundle is None:
            return SimpleNamespace(inquiry="", answer=None, confidence=0.0)

        # Already source-bundle shaped
        if (
            hasattr(bundle, "inquiry")
            or hasattr(bundle, "answer")
            or hasattr(bundle, "confidence")
        ):
            return SimpleNamespace(
                inquiry=getattr(bundle, "inquiry", "") or "",
                answer=getattr(bundle, "answer", None),
                confidence=getattr(bundle, "confidence", 0.0),
            )

        # Dict bundle
        if isinstance(bundle, dict):
            return SimpleNamespace(
                inquiry=bundle.get("inquiry", "") or "",
                answer=bundle.get("answer"),
                confidence=bundle.get("confidence", 0.0),
            )

        # Nested source bundle
        source_bundle = getattr(bundle, "source_bundle", None)
        if source_bundle is not None:
            return SimpleNamespace(
                inquiry=getattr(source_bundle, "inquiry", "") or "",
                answer=getattr(source_bundle, "answer", None),
                confidence=getattr(source_bundle, "confidence", 0.0),
            )

        return SimpleNamespace(inquiry="", answer=None, confidence=0.0)

    # =========================================================
    # HELPERS
    # =========================================================

    def _build_semantic_text(self, inquiry_text: str, answer: str) -> str:
        combined = f"{inquiry_text} {answer}".strip().lower()

        for ch in (".", ",", "!", "?", ":", ";"):
            combined = combined.replace(ch, "")

        combined = " ".join(combined.split())
        return combined

    def _stable_key(self, inquiry_text: str, answer: str) -> int:
        cleaned = self._build_semantic_text(inquiry_text, answer)
        return abs(hash(cleaned)) % 100000

    def _safe_confidence(self, value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0