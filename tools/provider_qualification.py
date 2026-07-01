from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.model_runtime.model_registry import discover_local_models
from integration.model_runtime.provider_qualification import (
    LayerProbeResult,
    PromptProbeResult,
    ProviderQualificationReportWriter,
    ProviderQualificationRecord,
    ProviderQualificationSuite,
    TimeoutProbeExecutor,
)


def _layers(raw: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in raw.split(",") if item.strip())


def _contexts(raw: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in raw.split(",") if item.strip())


def _existing_records(path: Path) -> list[ProviderQualificationRecord]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for item in payload:
        records.append(_record_from_payload(item))
    return records


def _record_from_payload(item: dict) -> ProviderQualificationRecord:
    probes = []
    for probe in item.get("layer_probes", []):
        prompts = tuple(
            PromptProbeResult(**prompt)
            for prompt in probe.get("prompt_results", [])
        )
        probes.append(
            LayerProbeResult(
                **{
                    **probe,
                    "prompt_results": prompts,
                }
            )
        )
    return ProviderQualificationRecord(
        **{
            **item,
            "capabilities": tuple(item.get("capabilities", [])),
            "notes": tuple(item.get("notes", [])),
            "errors": tuple(item.get("errors", [])),
            "layer_probes": tuple(probes),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify discovered local GGUF providers before experiments."
    )
    parser.add_argument("--model-root", default=None)
    parser.add_argument("--layers", default="32,28,24,22,16,8,0")
    parser.add_argument("--contexts", default="8192,4096,2048")
    parser.add_argument("--probe-timeout", type=int, default=300)
    parser.add_argument("--max-tokens", type=int, default=48)
    parser.add_argument("--skip-model", action="append", default=[])
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_false", dest="resume")
    parser.add_argument("--json-path", default=str(ROOT / "reports" / "provider_qualification.json"))
    parser.add_argument("--markdown-path", default=str(ROOT / "reports" / "provider_qualification.md"))
    parser.add_argument("--health-path", default=str(ROOT / "reports" / "provider_health.md"))
    parser.add_argument(
        "--capability-db-path",
        default=str(ROOT / "data" / "model_runtime" / "provider_capabilities.json"),
    )
    args = parser.parse_args()

    models = discover_local_models(args.model_root)
    print(f"discovered={len(models)}", flush=True)
    skipped = {str(item).strip().lower() for item in args.skip_model if str(item).strip()}
    suite = ProviderQualificationSuite(
        executor=TimeoutProbeExecutor(
            timeout_seconds=args.probe_timeout,
            max_context=max(_contexts(args.contexts) or (2048,)),
            max_tokens=args.max_tokens,
        ),
        layer_candidates=_layers(args.layers),
        context_candidates=_contexts(args.contexts),
    )
    writer = ProviderQualificationReportWriter(
        json_path=args.json_path,
        markdown_path=args.markdown_path,
        health_path=args.health_path,
        capability_db_path=args.capability_db_path,
    )
    records = _existing_records(Path(args.json_path)) if args.resume else []
    completed = {record.model_name for record in records}
    if completed:
        print(f"resume_completed={len(completed)}", flush=True)
    for spec in sorted(models.values(), key=lambda item: item.name):
        if spec.name.lower() in skipped:
            print(f"skip_requested={spec.name}", flush=True)
            continue
        if spec.name in completed:
            print(f"skip_completed={spec.name}", flush=True)
            continue
        print(f"qualifying={spec.name}", flush=True)
        record = suite.qualify(spec)
        records.append(record)
        status = "qualified" if record.qualified else "failed"
        print(
            f"result={status} model={record.model_name} "
            f"layers={record.recommended_gpu_layers} "
            f"context={record.recommended_context} "
            f"tok_s={record.average_tokens_per_second}",
            flush=True,
        )
        writer.write(records)
        print(f"checkpoint_records={len(records)}", flush=True)

    writer.write(records)
    print(f"wrote={args.json_path}", flush=True)
    print(f"wrote={args.markdown_path}", flush=True)
    print(f"wrote={args.health_path}", flush=True)
    print(f"wrote={args.capability_db_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
