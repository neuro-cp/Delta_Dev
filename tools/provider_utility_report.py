from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.experience import ExperienceStore
from orchestration.novelty import NoveltyAnalyzer, ProviderUtilityProfiler


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def build_report(*, experience_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    experiences = ExperienceStore(experience_path).all()
    analyzer = NoveltyAnalyzer()
    reports = []
    for experience in experiences:
        report = analyzer.analyze(
            text=experience.content,
            required_capabilities=experience.metadata.get("required_capabilities", ()),
        )
        reports.append(
            type(report)(
                **{
                    **report.__dict__,
                    "metadata": {
                        **report.metadata,
                        "provider": experience.provenance.get("provider"),
                        "model_id": experience.provenance.get("model_id"),
                    },
                }
            )
        )
    profiles = ProviderUtilityProfiler().profile(reports)
    payload = {
        "experience_path": str(experience_path),
        "experience_count": len(experiences),
        "profiles": _jsonable(profiles),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile providers by generated experience utility."
    )
    parser.add_argument("--experience-path", required=True)
    parser.add_argument("--output-path")
    args = parser.parse_args()
    report = build_report(
        experience_path=Path(args.experience_path),
        output_path=Path(args.output_path) if args.output_path else None,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
