from __future__ import annotations

from typing import Any, Callable, List, Optional
from pathlib import Path

from integration.bridge.runtime_bootstrap import build_runtime
from integration.bridge.runtime_artifact_builder import RuntimeArtifactBuilder
from integration.bridge.runtime_artifact_store import RuntimeArtifactStore


class ReplayManager:
    """
    Orchestration-level replay queue and executor.

    Now extended with:
    - runtime execution BEFORE replay
    - artifact extraction (PFC/VTA/urgency)
    - sidecar artifact storage (semantic_id -> artifact)

    IMPORTANT:
    - memory/ is NOT modified
    - replay pipeline remains untouched
    - runtime is only used to build artifacts (no authority)
    """

    def __init__(
        self,
        replay_storage_pipeline_factory: Callable[[str], Any],
        *,
        replay_id_prefix: str = "bridge_replay",
        auto_flush_threshold: Optional[int] = None,
        verbose: bool = True,
        repo_root: Path = None,
        artifact_store=None,
    ):
        self._factory = replay_storage_pipeline_factory
        self._queue: List[Any] = []

        self._replay_id_prefix = replay_id_prefix
        self._counter = 0

        self._auto_flush_threshold = auto_flush_threshold
        self._verbose = verbose

        # 🔴 runtime + artifact system
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[2]

        self._runtime = build_runtime(repo_root)
        self._artifact_builder = RuntimeArtifactBuilder(self._runtime)
        self._artifact_store = artifact_store or RuntimeArtifactStore()

    # =========================================================
    # QUEUE OPERATIONS
    # =========================================================

    def enqueue(self, bundle: Any) -> None:
        self._queue.append(bundle)

        if self._verbose:
            print(f"[REPLAY] enqueued bundle (queue size={len(self._queue)})")

        if (
            self._auto_flush_threshold is not None
            and len(self._queue) >= self._auto_flush_threshold
        ):
            if self._verbose:
                print("[REPLAY] auto-threshold reached → triggering replay")
            self.run()

    def extend(self, bundles: List[Any]) -> None:
        for b in bundles:
            self.enqueue(b)

    def has_pending(self) -> bool:
        return len(self._queue) > 0

    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        if self._verbose:
            print("[REPLAY] clearing queue without execution")
        self._queue.clear()

    # =========================================================
    # REPLAY EXECUTION
    # =========================================================

    def run(self) -> Any:
        if not self._queue:
            if self._verbose:
                print("[REPLAY] nothing to process")
            return None

        replay_id = self._build_replay_id()

        if self._verbose:
            print(f"[REPLAY] starting run id={replay_id}")
            print(f"[REPLAY] processing {len(self._queue)} bundle(s)")

        try:
            pipeline = self._factory(replay_id)
            bundles = list(self._queue)

            # =====================================================
            # STEP 1 — BUILD RUNTIME ARTIFACTS
            # =====================================================
            bundle_artifacts = []

            for bundle in bundles:
                inquiry_text = None

                # primary
                if hasattr(bundle, "inquiry"):
                    inquiry_text = getattr(bundle, "inquiry")

                # fallback
                if not inquiry_text and hasattr(bundle, "source_bundle"):
                    sb = getattr(bundle, "source_bundle")
                    if sb and hasattr(sb, "inquiry"):
                        inquiry_text = getattr(sb, "inquiry")

                # dict fallback
                if not inquiry_text and isinstance(bundle, dict):
                    inquiry_text = bundle.get("inquiry")

                if not inquiry_text:
                    if self._verbose:
                        print("[REPLAY] WARNING: no inquiry found in bundle")
                    bundle_artifacts.append(None)
                    continue

                if self._verbose:
                    print(f"[REPLAY] building artifact for inquiry: {inquiry_text}")

                artifact = self._artifact_builder.build_from_text(inquiry_text)

                if self._verbose:
                    print(f"[REPLAY] artifact: {artifact}")

                bundle_artifacts.append(artifact)

            # =====================================================
            # STEP 2 — RUN REPLAY
            # =====================================================
            result = pipeline.run(bundles)

            if self._verbose:
                print("[REPLAY] pipeline execution complete")

            # =====================================================
            # STEP 3 — MAP SEMANTICS → ARTIFACTS
            # =====================================================
            stored = 0

            deltas = result if isinstance(result, list) else []

            for d in deltas:
                if not isinstance(d, dict):
                    continue

                semantic_id = d.get("semantic_id")
                inquiry = d.get("inquiry")

                if not semantic_id or not inquiry:
                    continue

                artifact = None

                def _normalize(x):
                    return str(x).strip().lower()

                for bundle, a in zip(bundles, bundle_artifacts):
                    b_inquiry = getattr(bundle, "inquiry", None)

                    if _normalize(b_inquiry) == _normalize(inquiry):
                        artifact = a
                        break

                if not artifact:
                    continue

                self._artifact_store.put(semantic_id, artifact)
                stored += 1

                if self._verbose:
                    print(f"[REPLAY] stored artifact for {semantic_id}")

            # =====================================================
            # FINAL REPORT
            # =====================================================
            if self._verbose:
                if stored == 0:
                    print("[REPLAY] no artifacts stored (no valid semantic_id/artifact matches)")
                else:
                    print(f"[REPLAY] stored {stored} artifact(s)")

        except Exception as e:
            print(f"[REPLAY] ERROR during execution: {e}")
            return None

        # =====================================================
        # CLEANUP
        # =====================================================
        self._queue.clear()

        if self._verbose:
            print("[REPLAY] queue cleared")

        return result
    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    def _build_replay_id(self) -> str:
        replay_id = f"{self._replay_id_prefix}_{self._counter}"
        self._counter += 1
        return replay_id

    # =========================================================
    # DEBUG / INSPECTION
    # =========================================================

    def dump_queue(self) -> None:
        print("\n[REPLAY] queue contents:")
        if not self._queue:
            print("  (empty)")
        else:
            for i, item in enumerate(self._queue):
                print(f"  {i}: {type(item)}")
        print()

    def summary(self) -> dict[str, Any]:
        return {
            "pending": len(self._queue),
            "auto_flush_threshold": self._auto_flush_threshold,
            "replay_counter": self._counter,
        }