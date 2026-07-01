from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Delta Console</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      background: #101214;
      color: #e8edf2;
    }
    body { margin: 0; background: #101214; }
    header {
      height: 52px; display: flex; align-items: center; justify-content: space-between;
      padding: 0 18px; border-bottom: 1px solid #2a3138; background: #15191d;
    }
    h1 { font-size: 18px; margin: 0; font-weight: 650; }
    main {
      display: grid; grid-template-columns: repeat(4, minmax(230px, 1fr));
      gap: 10px; padding: 10px;
    }
    section {
      background: #171c21; border: 1px solid #2b333b; border-radius: 6px;
      min-height: 170px; overflow: hidden;
    }
    h2 {
      font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
      margin: 0; padding: 9px 10px; border-bottom: 1px solid #2b333b;
      color: #a9b6c2; background: #1c2228;
    }
    pre {
      white-space: pre-wrap; word-break: break-word; margin: 0; padding: 10px;
      font-size: 12px; line-height: 1.35; color: #d8e0e7;
    }
    .wide { grid-column: span 2; }
    .tall { min-height: 260px; }
    .status { color: #95d5b2; font-size: 12px; }
    @media (max-width: 1100px) { main { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 680px) { main { grid-template-columns: 1fr; } .wide { grid-column: span 1; } }
  </style>
</head>
<body>
  <header>
    <h1>Delta Console</h1>
    <div class="status" id="status">loading</div>
  </header>
  <main>
    <section><h2>Current Tick</h2><pre id="tick"></pre></section>
    <section><h2>Health</h2><pre id="health"></pre></section>
    <section><h2>Metrics</h2><pre id="metrics"></pre></section>
    <section><h2>Prediction Quality</h2><pre id="predictionQuality"></pre></section>
    <section><h2>Models</h2><pre id="models"></pre></section>
    <section><h2>Active Provider</h2><pre id="activeProvider"></pre></section>
    <section><h2>GPU</h2><pre id="gpu"></pre></section>
    <section><h2>Experiment Queue</h2><pre id="experimentQueue"></pre></section>
    <section><h2>Experiment Utility</h2><pre id="experimentUtility"></pre></section>
    <section><h2>Inference Observatory</h2><pre id="modelObservatory"></pre></section>
    <section><h2>Provider Effectiveness</h2><pre id="providerEffectiveness"></pre></section>
    <section><h2>Knowledge Quality</h2><pre id="knowledgeQuality"></pre></section>
    <section><h2>Agency Proposal</h2><pre id="agency"></pre></section>
    <section><h2>Goals</h2><pre id="goals"></pre></section>
    <section><h2>Plans</h2><pre id="plans"></pre></section>
    <section><h2>Predictions</h2><pre id="predictions"></pre></section>
    <section><h2>Contradictions</h2><pre id="contradictions"></pre></section>
    <section><h2>Relationships</h2><pre id="relationships"></pre></section>
    <section><h2>Reflection Quality</h2><pre id="reflectionQuality"></pre></section>
    <section><h2>Semantic Knowledge</h2><pre id="knowledge"></pre></section>
    <section class="wide"><h2>Recent Runtime Events</h2><pre id="timeline"></pre></section>
    <section class="wide"><h2>Recent Inference Events</h2><pre id="modelEvents"></pre></section>
    <section class="wide"><h2>Generated Experiences</h2><pre id="generatedExperiences"></pre></section>
    <section class="wide"><h2>World Model</h2><pre id="worldModel"></pre></section>
    <section class="wide"><h2>Recent Memories</h2><pre id="memories"></pre></section>
    <section class="wide"><h2>Learning</h2><pre id="learning"></pre></section>
    <section class="wide tall"><h2>Self Model</h2><pre id="selfmodel"></pre></section>
  </main>
  <script>
    const put = (id, value) => {
      document.getElementById(id).textContent = JSON.stringify(value, null, 2);
    };
    async function refresh() {
      const response = await fetch('/api/state', { cache: 'no-store' });
      const state = await response.json();
      document.getElementById('status').textContent = 'updated ' + new Date().toLocaleTimeString();
      put('tick', state.current_tick);
      put('health', state.self_model.cognitive_health);
      put('metrics', state.self_model.metrics);
      put('predictionQuality', state.prediction_quality);
      put('models', state.models);
      put('activeProvider', state.active_provider);
      put('gpu', state.gpu);
      put('experimentQueue', state.experiment_queue);
      put('experimentUtility', state.experiment_utility);
      put('modelObservatory', state.model_observatory);
      put('providerEffectiveness', state.provider_effectiveness);
      put('knowledgeQuality', state.knowledge_quality);
      put('agency', state.latest_agency);
      put('goals', state.goals);
      put('plans', state.plans);
      put('predictions', state.predictions);
      put('contradictions', state.contradictions);
      put('relationships', state.relationships);
      put('reflectionQuality', state.reflection_quality);
      put('knowledge', state.semantic_knowledge);
      put('timeline', state.runtime_events);
      put('modelEvents', state.model_inference_events);
      put('generatedExperiences', state.generated_experiences);
      put('worldModel', state.world_model);
      put('memories', state.memories);
      put('learning', state.learning);
      put('selfmodel', state.self_model.self_observations);
    }
    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>
"""


def _read_jsonl(path: Path, limit: int = 20) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records[-limit:]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gpu_status() -> dict:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=1.5,
        ).strip()
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    if not output:
        return {"available": False}
    name, used, total, utilization = [part.strip() for part in output.split(",", 3)]
    return {
        "available": True,
        "name": name,
        "memory_used_mb": int(float(used)),
        "memory_total_mb": int(float(total)),
        "utilization_percent": int(float(utilization)),
    }


def _experiment_dashboard_state() -> dict:
    from orchestration.experiments import ExperimentQueueStore

    store = ExperimentQueueStore(
        ROOT / "data" / "experiments" / "experiment_queue.jsonl",
        ROOT / "data" / "experiments" / "experiment_results.jsonl",
    )
    provider_status = _read_json(ROOT / "data" / "model_runtime" / "provider_status.json")
    summary = store.summary(active_provider=provider_status)
    latest = [
        {
            "item_id": result.item_id,
            "status": result.status,
            "route": result.route,
            "provider_model": result.provider_model,
            "utility_score": result.utility_score,
            "information_gain_score": result.information_gain_score,
            "surprise_score": result.surprise_score,
            "generated_experience_count": result.generated_experience_count,
        }
        for result in summary.latest_results[-5:]
    ]
    return {
        "active_provider": provider_status or {"loaded": False},
        "queue": {
            "queued": summary.queued,
            "running": summary.running,
            "completed": summary.completed,
            "failed": summary.failed,
        },
        "utility": {
            "cumulative_utility": summary.cumulative_utility,
            "latest_results": latest,
        },
    }


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _state() -> dict:
    from integration.model_runtime import (
        ModelObservatory,
        ProviderLearningEngine,
        list_available_models,
    )
    from knowledge import (
        ContradictionEngine,
        KnowledgeQualityAnalyzer,
        PredictionEngine,
        SemanticKnowledgeStore,
    )
    from learning.region import LearningStore
    from memory.persistent import MemoryStore
    from memory.relationships import RelationshipStore
    from orchestration.agency import AgencyRegion, GoalStore, PlanStore
    from orchestration.experience import ExperienceStore
    from orchestration.self_model import SelfModelRegion
    from orchestration.world_model import WorldModelStore

    memory = MemoryStore(ROOT / "data" / "memory" / "persistent_memory.jsonl")
    relationships = RelationshipStore(ROOT / "data" / "memory" / "relationships.jsonl")
    learning = LearningStore(ROOT / "data" / "learning" / "learning_records.jsonl")
    knowledge = SemanticKnowledgeStore(ROOT / "data" / "knowledge" / "semantic_knowledge.jsonl")
    contradictions = ContradictionEngine(ROOT / "data" / "knowledge" / "contradictions.jsonl")
    predictions = PredictionEngine(ROOT / "data" / "knowledge" / "predictions.jsonl")
    goals = GoalStore(ROOT / "data" / "agency" / "goals.jsonl")
    plans = PlanStore(ROOT / "data" / "agency" / "plans.jsonl")
    model_observatory = ModelObservatory(ROOT / "data" / "model_runtime" / "inference_events.jsonl")
    experiences = ExperienceStore(ROOT / "data" / "experience" / "generated_experiences.jsonl")
    world_model = WorldModelStore(ROOT / "data" / "world_model" / "world_model.jsonl")
    events = _read_jsonl(ROOT / "data" / "runtime" / "events.jsonl")
    learning_records = learning.all()
    relationship_records = relationships.latest()
    contradiction_records = contradictions.latest()
    snapshot = SelfModelRegion(
        memory_store=memory,
        relationship_store=relationships,
        learning_store=learning,
        semantic_store=knowledge,
        contradiction_engine=contradictions,
        prediction_engine=predictions,
    ).generate()
    latest_agency = AgencyRegion().propose(
        goals=goals.active(),
        self_model=snapshot.to_dict(),
    ).to_dict()
    available_models = list_available_models()
    inference_events = model_observatory.all()
    provider_profiles = ProviderLearningEngine().profiles(inference_events)
    experiment_dashboard = _experiment_dashboard_state()
    knowledge_quality = KnowledgeQualityAnalyzer().analyze_many(
        knowledge.latest()[-20:],
        predictions=predictions.latest(),
        contradictions=contradiction_records,
        relationships=relationship_records,
    )
    world_snapshots = world_model.all()
    return {
        "current_tick": events[-1] if events else None,
        "runtime_events": events[-10:],
        "memories": _jsonable(memory.all()[-10:]),
        "relationships": _jsonable(relationship_records[-20:]),
        "learning": _jsonable(learning_records[-10:]),
        "semantic_knowledge": _jsonable(knowledge.latest()[-20:]),
        "predictions": _jsonable(predictions.latest()[-20:]),
        "prediction_quality": predictions.quality_metrics(),
        "models": _jsonable(
            {
                name: {
                    "provider": spec.provider,
                    "family": spec.family,
                    "quantization": spec.quantization,
                    "tier": spec.tier,
                    "context_length": spec.context_length,
                    "capabilities": spec.capabilities,
                    "size_bytes": spec.size_bytes,
                    "path": spec.path,
                    "mmproj_path": spec.mmproj_path,
                }
                for name, spec in sorted(available_models.items())
            }
        ),
        "active_provider": experiment_dashboard["active_provider"],
        "gpu": _gpu_status(),
        "experiment_queue": experiment_dashboard["queue"],
        "experiment_utility": experiment_dashboard["utility"],
        "model_observatory": model_observatory.metrics(),
        "model_inference_events": _jsonable(inference_events[-10:]),
        "provider_effectiveness": _jsonable(provider_profiles),
        "knowledge_quality": _jsonable(knowledge_quality),
        "generated_experiences": _jsonable(experiences.all()[-10:]),
        "world_model": world_snapshots[-1] if world_snapshots else None,
        "contradictions": _jsonable(contradiction_records[-20:]),
        "reflection_quality": [
            {
                "learning_id": record.learning_id,
                "cycle_id": record.cycle_id,
                "quality": record.metadata.get("reflection_quality"),
            }
            for record in learning_records[-10:]
            if record.metadata.get("reflection_quality") is not None
        ],
        "goals": _jsonable(goals.active()),
        "plans": _jsonable(plans.all()[-10:]),
        "latest_agency": _jsonable(latest_agency),
        "self_model": snapshot.to_dict(),
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            payload = json.dumps(_state(), indent=2, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        payload = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Delta inspection console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Delta Console: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Delta Console stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
