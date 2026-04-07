from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class ReplayStoragePipeline:

    def __init__(self, replay_id: str | None = None):
        self.replay_id = replay_id or "replay_local"
        self._accumulator = {}

    # =========================================================
    # MAIN
    # =========================================================

    def run(self, bundles) -> list[dict]:
        proposals = self._extract_proposals(bundles)

        if not proposals:
            proposals = self._inject_synthetic_proposals(bundles)

        return self._build_semantic_records(proposals)

    # =========================================================
    # PROPOSAL EXTRACTION
    # =========================================================

    def _extract_proposals(self, bundles) -> list[Any]:
        proposals: list[Any] = []

        for bundle in bundles:
            if bundle is None:
                continue

            # Already proposal-like
            if hasattr(bundle, "source_bundle") or hasattr(bundle, "deltas"):
                proposals.append(bundle)
                continue

            # Bundle has proposals
            bundle_proposals = getattr(bundle, "proposals", None)
            if bundle_proposals:
                proposals.extend(bundle_proposals)
                continue

            # Dict case
            if isinstance(bundle, dict):
                dict_proposals = bundle.get("proposals")
                if dict_proposals:
                    proposals.extend(dict_proposals)

        return proposals

    # =========================================================
    # SYNTHETIC PROPOSALS
    # =========================================================

    def _inject_synthetic_proposals(self, bundles) -> list[Any]:
        synthetic = []

        for bundle in bundles:
            source_bundle = self._coerce_source_bundle(bundle)

            answer = getattr(source_bundle, "answer", None)
            if not answer:
                continue

            proposal = SimpleNamespace(
                source_bundle=source_bundle,
                deltas=[
                    SimpleNamespace(
                        target="synthetic",
                        delta_type="synthetic",
                    )
                ],
                bounded=True,
                replay_consistent=True,
            )

            synthetic.append(proposal)

        return synthetic

    # =========================================================
    # ACCUMULATION LOGIC
    # =========================================================

    def _build_semantic_records(self, proposals) -> list[dict]:
        applied: list[dict] = []

        for proposal in proposals:
            source_bundle = getattr(proposal, "source_bundle", None)
            if source_bundle is None:
                continue

            answer = getattr(source_bundle, "answer", None)
            inquiry_text = getattr(source_bundle, "inquiry", "") or ""

            if not answer:
                continue

            deltas = getattr(proposal, "deltas", None) or []

            for delta in deltas:
                combined = self._build_semantic_text(inquiry_text, answer)
                semantic_id = f"sem:{self._normalize_semantic(combined)}"

                if semantic_id in self._accumulator:
                    record = self._accumulator[semantic_id]
                    record["recurrence_count"] += 1
                    record["supporting_episode_ids"].append(self.replay_id)

                    if record["recurrence_count"] > 2:
                        record["stability_classification"] = "stable"
                else:
                    record = {
                        "semantic_id": semantic_id,
                        "pattern_type": getattr(delta, "delta_type", "unknown"),
                        "supporting_episode_ids": [self.replay_id],
                        "recurrence_count": 1,
                        "persistence_span": 1,
                        "stability_classification": "unstable",
                        "inquiry": inquiry_text,
                        "answer": answer,
                        "confidence": 1.0,
                        "source_replay_id": self.replay_id,
                    }
                    self._accumulator[semantic_id] = record

                applied.append(self._accumulator[semantic_id])

        return applied

    # =========================================================
    # BUNDLE COERCION
    # =========================================================

    def _coerce_source_bundle(self, bundle):
        if bundle is None:
            return SimpleNamespace(inquiry="", answer=None, confidence=0.0)

        if hasattr(bundle, "inquiry") or hasattr(bundle, "answer"):
            return SimpleNamespace(
                inquiry=getattr(bundle, "inquiry", "") or "",
                answer=getattr(bundle, "answer", None),
                confidence=getattr(bundle, "confidence", 0.0),
            )

        if isinstance(bundle, dict):
            return SimpleNamespace(
                inquiry=bundle.get("inquiry", "") or "",
                answer=bundle.get("answer"),
                confidence=bundle.get("confidence", 0.0),
            )

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
        combined = " ".join(combined.split())
        return combined

    def _normalize_semantic(self, text: str) -> str:
        return str(text).strip().lower()