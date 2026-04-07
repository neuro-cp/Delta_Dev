import os
from typing import Any

from orchestration.loop.cognitive_loop import CognitiveLoop
from integration.model_runtime.model_router import ModelRouter

# existing system components
from memory.replay_storage.replay_storage_pipeline import ReplayStoragePipeline
from orchestration.memory.learning_integrator import LearningIntegrator

# recall system
from memory.replay_recall.replay_recall_pipeline import ReplayRecallPipeline


# =========================================
# ENV SETUP
# =========================================
def setup_env():
    if not os.getenv("RUN_REAL_MODELS"):
        os.environ["RUN_REAL_MODELS"] = input("run real models? (1/0): ").strip()

    if not os.getenv("DELTA_MACHINE_PROFILE"):
        os.environ["DELTA_MACHINE_PROFILE"] = input("env (desktop/laptop): ").strip().lower()

    if not os.getenv("DELTA_MAX_MODELS"):
        val = input("max models (optional): ").strip()
        if val:
            os.environ["DELTA_MAX_MODELS"] = val


# =========================================
# FACTORIES
# =========================================

def build_replay_storage_pipeline(replay_id: str) -> ReplayStoragePipeline:
    return ReplayStoragePipeline(replay_id=replay_id)


# 🔥 GLOBAL REGISTRY (NOW ACTUALLY POPULATED)
GLOBAL_SEMANTIC_REGISTRY = []


# =========================================
# SAFE LEARNING BUNDLE
# =========================================

class SimpleLearningBundle:
    def __init__(self, inquiry: str, answer: str, confidence: float, source: str):
        self.inquiry = str(inquiry)
        self.answer = str(answer)
        self.confidence = float(confidence)
        self.source = str(source)

        self.pattern_counts = {}
        self.semantic_activation_snapshots = []

    def __repr__(self):
        return (
            f"SimpleLearningBundle(inquiry={self.inquiry[:30]!r}, "
            f"confidence={self.confidence}, source={self.source})"
        )


def build_learning_bundle(inquiry: Any, answer: str, confidence: float, source: str):
    return SimpleLearningBundle(
        inquiry=inquiry.raw_text,
        answer=answer,
        confidence=confidence,
        source=source,
    )


# =========================================
# LOOP
# =========================================
def main():
    setup_env()

    router = ModelRouter()

    # recall pipeline
    recall_pipeline = ReplayRecallPipeline()

    loop = CognitiveLoop(
        model_router=router,
        replay_storage_pipeline_factory=build_replay_storage_pipeline,
        learning_bundle_factory=build_learning_bundle,
        replay_recall_pipeline=recall_pipeline,
        recall_registry=GLOBAL_SEMANTIC_REGISTRY,
    )

    print("\n=== DELTA MEMORY / REPLAY LOOP ===\n")
    print("commands:")
    print("  replay  -> run queued replay")
    print("  queue   -> show replay queue")
    print("  exit    -> quit\n")

    executor = getattr(loop, "executor", None)
    replay_manager = getattr(executor, "_replay_manager", None)

    if executor is None:
        print("[WARN] executor not found on loop")

    if replay_manager is None:
        print("[WARN] replay manager not wired")
    else:
        print("[OK] replay manager active")

    # =========================================
    # MAIN LOOP
    # =========================================
    while True:
        prompt = input("\nAsk (or command): ").strip()

        if prompt.lower() == "exit":
            break

        # ---------------------------------
        # REPLAY COMMAND
        # ---------------------------------
        if prompt.lower() == "replay":
            if replay_manager is None:
                print("[REPLAY] manager not available")
            else:
                result = replay_manager.run()

                # 🔥 FIXED: populate registry from replay output
                if result:
                    GLOBAL_SEMANTIC_REGISTRY.clear()

                    for d in result:
                        if not isinstance(d, dict):
                            continue

                        sem_id = d.get("semantic_id")
                        inquiry = d.get("inquiry")
                        answer = d.get("answer")

                        if not sem_id:
                            continue

                    GLOBAL_SEMANTIC_REGISTRY.append(
                        type("SemanticStub", (), {
                            "semantic_id": sem_id,
                            "recurrence_count": 1,
                            "inquiry": inquiry,
                            "answer": answer,

                            # 🔥 REQUIRED FOR MATCHER
                            "tags": {
                                "regions": ["pfc", "vta", "urgency"]
                            }
                        })()
                    )

                    print(f"[RECALL] registry updated: {len(GLOBAL_SEMANTIC_REGISTRY)} items")

            continue

        # ---------------------------------
        # QUEUE INSPECTION
        # ---------------------------------
        if prompt.lower() == "queue":
            if replay_manager is None:
                print("[REPLAY] manager not available")
            else:
                replay_manager.dump_queue()
            continue

        # ---------------------------------
        # NORMAL EXECUTION
        # ---------------------------------
        result_bundle = loop.run(prompt)
        result = result_bundle["result"]

        print("\n--- RESULT ---")
        print("route:", result.route_type)
        print("output:", result.output)
        print("confidence:", result.confidence)

        if hasattr(result, "artifacts") and result.artifacts:
            print("artifacts:", list(result.artifacts.keys()))

        print("--------------")

        if replay_manager is not None:
            print(f"[REPLAY] pending bundles: {replay_manager.size()}")


# =========================================
# ENTRY
# =========================================
if __name__ == "__main__":
    main()