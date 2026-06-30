from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


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
      display: grid; grid-template-columns: repeat(4, minmax(220px, 1fr));
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
    <section><h2>Agency Proposal</h2><pre id="agency"></pre></section>
    <section><h2>Goals</h2><pre id="goals"></pre></section>
    <section><h2>Plans</h2><pre id="plans"></pre></section>
    <section><h2>Predictions</h2><pre id="predictions"></pre></section>
    <section><h2>Semantic Knowledge</h2><pre id="knowledge"></pre></section>
    <section class="wide"><h2>Recent Runtime Events</h2><pre id="timeline"></pre></section>
    <section class="wide"><h2>Recent Memories</h2><pre id="memories"></pre></section>
    <section class="wide"><h2>Learning</h2><pre id="learning"></pre></section>
    <section class="wide"><h2>Self Model</h2><pre id="selfmodel"></pre></section>
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
      put('agency', state.latest_agency);
      put('goals', state.goals);
      put('plans', state.plans);
      put('predictions', state.predictions);
      put('knowledge', state.semantic_knowledge);
      put('timeline', state.runtime_events);
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


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _state() -> dict:
    from knowledge import ContradictionEngine, PredictionEngine, SemanticKnowledgeStore
    from learning.region import LearningStore
    from memory.persistent import MemoryStore
    from memory.relationships import RelationshipStore
    from orchestration.agency import AgencyRegion, GoalStore, PlanStore
    from orchestration.self_model import SelfModelRegion

    memory = MemoryStore(ROOT / "data" / "memory" / "persistent_memory.jsonl")
    relationships = RelationshipStore(ROOT / "data" / "memory" / "relationships.jsonl")
    learning = LearningStore(ROOT / "data" / "learning" / "learning_records.jsonl")
    knowledge = SemanticKnowledgeStore(ROOT / "data" / "knowledge" / "semantic_knowledge.jsonl")
    contradictions = ContradictionEngine(ROOT / "data" / "knowledge" / "contradictions.jsonl")
    predictions = PredictionEngine(ROOT / "data" / "knowledge" / "predictions.jsonl")
    goals = GoalStore(ROOT / "data" / "agency" / "goals.jsonl")
    plans = PlanStore(ROOT / "data" / "agency" / "plans.jsonl")
    events = _read_jsonl(ROOT / "data" / "runtime" / "events.jsonl")
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
    return {
        "current_tick": events[-1] if events else None,
        "runtime_events": events[-10:],
        "memories": _jsonable(memory.all()[-10:]),
        "relationships": _jsonable(relationships.all()[-10:]),
        "learning": _jsonable(learning.all()[-10:]),
        "semantic_knowledge": _jsonable(knowledge.latest()[-20:]),
        "predictions": _jsonable(predictions.all()[-20:]),
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
