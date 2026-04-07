from __future__ import annotations

from typing import Any, Callable, List, Optional


class ReplayManager:
    """
    Orchestration-level replay queue and executor.

    This component is responsible for:
    - collecting learning bundles (from executor / bridge layer)
    - deferring execution (no immediate replay)
    - triggering replay explicitly (manual or scheduled)
    - preserving full separation from runtime dynamics

    IMPORTANT:
    - This does NOT modify runtime state directly
    - This does NOT mutate memory registries directly
    - This only invokes ReplayStoragePipeline.run(...)
    """

    def __init__(
        self,
        replay_storage_pipeline_factory: Callable[[str], Any],
        *,
        replay_id_prefix: str = "bridge_replay",
        auto_flush_threshold: Optional[int] = None,
        verbose: bool = True,
    ):
        """
        Args:
            replay_storage_pipeline_factory:
                Callable(replay_id) -> ReplayStoragePipeline instance

            replay_id_prefix:
                Prefix used when generating replay IDs

            auto_flush_threshold:
                If set, automatically triggers replay when queue reaches N items

            verbose:
                Enables debug printing
        """
        self._factory = replay_storage_pipeline_factory
        self._queue: List[Any] = []

        self._replay_id_prefix = replay_id_prefix
        self._counter = 0

        self._auto_flush_threshold = auto_flush_threshold
        self._verbose = verbose

    # =========================================================
    # QUEUE OPERATIONS
    # =========================================================

    def enqueue(self, bundle: Any) -> None:
        """
        Add a learning bundle to the replay queue.

        This does NOT trigger replay immediately.
        """
        self._queue.append(bundle)

        if self._verbose:
            print(f"[REPLAY] enqueued bundle (queue size={len(self._queue)})")

        # Optional auto-flush
        if (
            self._auto_flush_threshold is not None
            and len(self._queue) >= self._auto_flush_threshold
        ):
            if self._verbose:
                print("[REPLAY] auto-threshold reached → triggering replay")
            self.run()

    def extend(self, bundles: List[Any]) -> None:
        """
        Add multiple bundles at once.
        """
        for b in bundles:
            self.enqueue(b)

    def has_pending(self) -> bool:
        return len(self._queue) > 0

    def size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        """
        Clear queue without running replay (debug use only).
        """
        if self._verbose:
            print("[REPLAY] clearing queue without execution")
        self._queue.clear()

    # =========================================================
    # REPLAY EXECUTION
    # =========================================================

    def run(self) -> None:
        """
        Execute replay pipeline on all queued bundles.

        This is the ONLY place replay is triggered.
        """
        if not self._queue:
            if self._verbose:
                print("[REPLAY] nothing to process")
            return

        replay_id = self._build_replay_id()

        if self._verbose:
            print(f"[REPLAY] starting run id={replay_id}")
            print(f"[REPLAY] processing {len(self._queue)} bundle(s)")

        try:
            pipeline = self._factory(replay_id)

            # Defensive copy (avoid mutation during execution)
            bundles = list(self._queue)

            result = pipeline.run(bundles)
            
            if self._verbose:
                print("[REPLAY] pipeline execution complete")

        except Exception as e:
            print(f"[REPLAY] ERROR during execution: {e}")
            return

        # Only clear queue AFTER successful execution
        self._queue.clear()

        if self._verbose:
            print("[REPLAY] queue cleared")
        
        return result

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    def _build_replay_id(self) -> str:
        """
        Generate deterministic replay ID.
        """
        replay_id = f"{self._replay_id_prefix}_{self._counter}"
        self._counter += 1
        return replay_id

    # =========================================================
    # DEBUG / INSPECTION
    # =========================================================

    def dump_queue(self) -> None:
        """
        Print queue contents (for debugging).
        """
        print("\n[REPLAY] queue contents:")
        if not self._queue:
            print("  (empty)")
        else:
            for i, item in enumerate(self._queue):
                print(f"  {i}: {type(item)}")
        print()

    def summary(self) -> dict[str, Any]:
        """
        Return structured state (for inspection / testing).
        """
        return {
            "pending": len(self._queue),
            "auto_flush_threshold": self._auto_flush_threshold,
            "replay_counter": self._counter,
        }