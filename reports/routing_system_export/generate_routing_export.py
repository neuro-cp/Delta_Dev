from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "routing_system_export"
OUT.mkdir(parents=True, exist_ok=True)


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace").strip()


BRANCH = git(["branch", "--show-current"])
HEAD = git(["rev-parse", "HEAD"])
STATUS = subprocess.check_output(["git", "status", "--short", "--branch"], cwd=ROOT, text=True, encoding="utf-8", errors="replace")

CATEGORIES: dict[str, list[str]] = {
    "ACTIVE_RUNTIME": [
        "DELTA.py",
        "orchestration/runtime/delta_1_4_live_wikipedia_runtime.py",
        "orchestration/runtime/rc2_conversational_mode_router.py",
    ],
    "ACTIVE_SUPPORTING_STATE": [
        "orchestration/runtime/rc45_discourse_cognition_bridge.py",
        "orchestration/runtime/rc2_cognitive_episode.py",
        "orchestration/runtime/continuous_runtime_controller.py",
        "orchestration/runtime/delta_1_2_live_runtime.py",
        "orchestration/runtime/delta_1_6_operational_autonomy.py",
        "orchestration/runtime/delta_1_0_common.py",
    ],
    "ACTIVE_RETRIEVAL": [
        "orchestration/runtime/rc2_developmental_concept_memory.py",
        "orchestration/runtime/rc2_storage_adapter.py",
        "orchestration/runtime/rc2_working_reasoning_set.py",
        "orchestration/runtime/rc2_analogy_engine.py",
        "orchestration/runtime/rc2_contradiction_engine.py",
        "orchestration/runtime/delta_1_5_developmental_cognition.py",
    ],
    "ACTIVE_MODEL_ROUTING": [
        "integration/model_runtime/model_registry.py",
        "integration/model_runtime/provider_manager.py",
        "integration/model_runtime/gguf_model_runner.py",
        "scripts/delta_rc2_local_model_infer.py",
    ],
    "ACTIVE_GOVERNANCE": [
        "orchestration/runtime/rc1_operator_console.py",
        "orchestration/runtime/rc2_render_correction.py",
        "orchestration/runtime/v17_provider_assisted_unknown_answer.py",
        "orchestration/runtime/delta_1_1_development_loop.py",
    ],
    "ACTIVE_RESPONSE_COMPOSITION": [
        "orchestration/runtime/rc2_natural_conversation_renderer.py",
        "orchestration/runtime/rc2_route_arbitration.py",
        "orchestration/runtime/pc1_pragmatic_cognition.py",
        "orchestration/runtime/v29_local_answer_engine.py",
    ],
    "DORMANT_OR_OBSOLETE": [
        "orchestration/runtime/integrated_cognitive_runtime.py",
        "orchestration/runtime/rc3_ui_capability_adapter.py",
        "orchestration/runtime/rc4_ui_capability_adapter.py",
        "orchestration/runtime/rc5_ui_capability_adapter.py",
        "orchestration/runtime/rc6_governed_external_intelligence.py",
        "orchestration/runtime/rc7_governed_development_loop.py",
        "orchestration/runtime/rc11_rc12_systems_plateau.py",
        "integration/model_runtime/routing_policy.py",
    ],
    "UNCERTAIN": [],
}

RESPONSIBILITY = {
    "DELTA.py": "Tk application, launch entry point, chat submission handler, pending UI state, live-runtime worker dispatch, and final response insertion.",
    "orchestration/runtime/delta_1_4_live_wikipedia_runtime.py": "Live runtime bridge; first live-mode receiver for raw operator text; arbitrates lifecycle controls, pending approvals, Wikipedia, local-model approvals, operational self-model, and fallback RC2 conversation.",
    "orchestration/runtime/rc2_conversational_mode_router.py": "Primary non-live conversation router; classifies intent, selects local model lane, orders conversation/retrieval/follow-up/provider/local-model routes, builds payloads, and renders responses.",
    "orchestration/runtime/rc45_discourse_cognition_bridge.py": "UI-side discourse frame and preemption rules for report/pilot/operator follow-up shortcuts before RC2 routing.",
    "orchestration/runtime/rc2_cognitive_episode.py": "Working-memory episode and follow-up/pronoun/reference resolution attached to RC2 payloads.",
    "orchestration/runtime/continuous_runtime_controller.py": "Live runtime lifecycle controller and background objective/event/state arbitration surfaced in status and live decisions.",
    "orchestration/runtime/delta_1_2_live_runtime.py": "Live runtime state, event queue, wake cycle, journal, and future-surface permission scaffolding.",
    "orchestration/runtime/delta_1_6_operational_autonomy.py": "Operational self-model, autonomy status, background cycle, initiative/inquiry/proposal formation.",
    "orchestration/runtime/delta_1_0_common.py": "Shared timestamps, stable ids, and safety metadata used by live routing artifacts.",
    "orchestration/runtime/rc2_developmental_concept_memory.py": "Approved concept retrieval, browsing, multi-concept retrieval, candidate concept formation, approval, relevance gates, and compact support packets.",
    "orchestration/runtime/rc2_storage_adapter.py": "SQLite/JSONL substrate adapter used by UI database search and anchor/nearby concept retrieval.",
    "orchestration/runtime/rc2_working_reasoning_set.py": "Ephemeral multi-concept working set selector for complex prompts.",
    "orchestration/runtime/rc2_analogy_engine.py": "Analogy route detection and structural mapping payloads.",
    "orchestration/runtime/rc2_contradiction_engine.py": "Contradiction route detection and comparison payloads.",
    "orchestration/runtime/delta_1_5_developmental_cognition.py": "Wikipedia evidence to governed developmental observation, promotion candidate, and operator inquiry.",
    "integration/model_runtime/model_registry.py": "Local model discovery and model specs used by lane selection.",
    "integration/model_runtime/provider_manager.py": "One-resident-model local inference lifecycle manager used by UI/live approved local calls.",
    "integration/model_runtime/gguf_model_runner.py": "GGUF llama.cpp runner invoked by ProviderManager.",
    "scripts/delta_rc2_local_model_infer.py": "Fallback subprocess helper for local model inference.",
    "orchestration/runtime/rc1_operator_console.py": "Advanced operator substrate functions retained and still imported by RC2 mode routes and UI advanced panels.",
    "orchestration/runtime/rc2_render_correction.py": "Early UI route for render-correction requests and RC2 render-correction payloads.",
    "orchestration/runtime/v17_provider_assisted_unknown_answer.py": "Provider consent and unknown-answer gate used for preview and approved provider support.",
    "orchestration/runtime/delta_1_1_development_loop.py": "Wikipedia permission profile schema used by live runtime.",
    "orchestration/runtime/rc2_natural_conversation_renderer.py": "Natural response post-processing for RC2 payload answers.",
    "orchestration/runtime/rc2_route_arbitration.py": "Route arbitration trace and safety normalization attached to RC2 payloads.",
    "orchestration/runtime/pc1_pragmatic_cognition.py": "UI-side pragmatic answer shortcut before pending-action/RC2 routing.",
    "orchestration/runtime/v29_local_answer_engine.py": "Local deterministic answer engine used inside RC2 local conversation answer path.",
}


def existing_files() -> list[str]:
    files: list[str] = []
    for group_files in CATEGORIES.values():
        for item in group_files:
            if (ROOT / item).exists() and item not in files:
                files.append(item)
    return files


def defs(path: str) -> list[tuple[int, str, str]]:
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            found.append((node.lineno, kind, node.name))
    return sorted(found)[:80]


def imports(path: str) -> list[str]:
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(("orchestration.", "integration.")):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            for name in node.names:
                if name.name.startswith(("orchestration.", "integration.")):
                    found.add(name.name)
    return sorted(found)


def discover_tests() -> list[str]:
    patterns = [
        "route_message",
        "handle_live_chat",
        "start_live_wikipedia_runtime",
        "render_route",
        "classify_intent",
        "resolve_working_memory_followup",
        "working_reasoning_set",
        "Wikipedia",
        "local_model",
        "pending_local_model",
        "greeting",
        "tell me more",
        "why",
        "pronoun",
        "pause",
        "suspend",
    ]
    tests: set[str] = set()
    for base in ("tests", "orchestration/tests", "integration/tests"):
        root = ROOT / base
        if not root.exists():
            continue
        for path in root.rglob("test*.py"):
            if "DELTA-75" in str(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern in text for pattern in patterns):
                tests.add(path.relative_to(ROOT).as_posix())
    return sorted(tests)


def write_inventory() -> None:
    lines = [
        "# Routing File Inventory",
        "",
        f"Repository: `{ROOT}`",
        f"Branch: `{BRANCH}`",
        f"HEAD: `{HEAD}`",
        "",
        "Initial runtime state:",
        "```text",
        STATUS.rstrip(),
        "```",
        "",
    ]
    for group, files in CATEGORIES.items():
        lines += [f"## {group}", ""]
        for item in files:
            if not (ROOT / item).exists():
                continue
            definition_text = ", ".join(f"{kind} {name} (L{line})" for line, kind, name in defs(item)[:25]) or "None detected"
            import_text = ", ".join(imports(item)[:20]) or "None in traced namespace"
            active = "Active in current Tk/live runtime" if group.startswith("ACTIVE") else "Retained/imported or adjacent, but not primary in current conversation route"
            lines += [
                f"### {item}",
                f"File: `{item}`",
                f"Active status: {active}",
                f"Primary responsibility: {RESPONSIBILITY.get(item, 'Routing-adjacent module identified by import/call tracing.')}",
                f"Key classes/functions: {definition_text}",
                "Called by: traced from `DELTA.py` imports, live runtime imports, or RC2 router imports; exact caller depends on route.",
                f"Calls into: {import_text}",
                "Routing decisions influenced: route precedence, retrieval/model/governance/state/rendering as applicable to this file.",
                "State read: message text, history, session/controller/model/concept/runtime state relevant to its route.",
                "State written: payload/session/UI/controller/concept candidate state where the module owns mutation; otherwise read-only route support.",
                f"Why this file belongs in the routing audit: {RESPONSIBILITY.get(item, 'It can influence the selected route, state arbitration, or rendered answer.')}",
                "",
            ]
    (OUT / "routing_file_inventory.md").write_text("\n".join(lines), encoding="utf-8")


def write_execution_map() -> None:
    text = f"""# Routing Execution Map

Repository: `{ROOT}`  
Branch: `{BRANCH}`  
HEAD: `{HEAD}`

## Verified Runtime State

- Active launch entry point: `DELTA.py`, `if __name__ == "__main__"` launches `DeltaApp`.
- Active Tk/UI conversation submission handler: `DELTA.py::DeltaApp._send_chat`.
- Function that first receives raw operator text in the active UI: `DeltaApp._send_chat`, via `self.chat_input.get().strip()`.
- Live-runtime raw text receiver: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py::handle_live_chat`.
- Non-live raw text router: `orchestration/runtime/rc2_conversational_mode_router.py::route_message`.
- Obsolete RC wrappers: RC3/RC4/RC5/RC6/RC7/RC11/RC12 UI adapters are retained/imported for panels, reports, or narrow pilot shortcuts; the active normal conversation path is `DELTA.py -> route_message` or `DELTA.py -> handle_live_chat -> route_message` fallback.

## Main Path

```text
operator types message
-> DELTA.py::DeltaApp._send_chat
-> append user text via DeltaApp._append_chat
-> build discourse frame via rc45_discourse_cognition_bridge.build_discourse_frame
-> if live_runtime_session.active:
   -> DeltaApp._begin_live_runtime_turn
   -> delta_1_4_live_wikipedia_runtime.handle_live_chat
   -> live arbitration: controller event, lifecycle, pending local model, pending promotion, help/memory/self-model/context, Wikipedia, fallback RC2
   -> LiveChatResponse(answer, route, payload)
   -> DeltaApp._complete_live_runtime_turn
   -> DeltaApp._append_chat("DELTA", response.answer)
-> else:
   -> UI preemption routes: render correction, local report inspection, RC6 pilot, RC45 report/pilot shortcuts, PC1 pragmatic answer, pending local/provider/model/deepening approvals, memory candidate commands
   -> rc2_conversational_mode_router.route_message
   -> rc2_conversational_mode_router.render_route
   -> DeltaApp._append_chat("DELTA", rendered)
```

## Branches

- greeting: `_send_chat` non-live -> `route_message` -> `classify_intent` / `classify_dialogue_act` -> social payload -> `render_route`; live mode falls through to `handle_live_chat` fallback `route_message` unless a higher live condition matches.
- ordinary conversation: `_send_chat` -> `route_message` -> `local_conversation_answer` / natural renderer / arbitration trace -> `render_route`.
- tell me more: non-live can match pending local-model deepening in `_send_chat` before RC2; otherwise `route_message` checks history answers, recent concept follow-up, working-memory follow-up, anchor follow-up, or local-model consent for follow-up.
- why?: `classify_intent` may classify analysis; `route_message` can choose working-memory follow-up, WRS, concept retrieval, or local conversation depending history and concept matches.
- pronoun follow-up: `route_message` -> `resolve_working_memory_followup` / `attach_episode`; active anchor may also drive `deepen_from_concept_anchor`.
- concept recall: `route_message` -> `query_approved_concepts`, `browse_approved_concepts`, `retrieve_multi_concept_set`, `build_working_reasoning_set`.
- Wikipedia: live only -> `handle_live_chat` -> `wikipedia_query_from_message` -> `retrieve_wikipedia_text` -> `run_wikipedia_developmental_cognition` -> promotion candidate/inquiry -> `render_wikipedia_answer`.
- local model: non-live `_send_chat` pending approval -> `route_message(... execute_local_model=True, provider_manager=...)`; live pending request -> `_run_approved_local_model_request` -> `route_message(... execute_local_model=True, provider_manager=...)` -> `execute_local_model_answer` -> `ProviderManager.infer` or subprocess fallback.
- self-model: live -> `is_operational_self_model_question` -> `answer_operational_self_model_question`; non-live self-description -> `classify_intent` / `local_conversation_answer`.
- pending approval: `_send_chat` handles UI-level pending provider/local/deepening before RC2; live `handle_live_chat` handles pending local-model and promotion inquiries before Wikipedia/fallback.
- pause: UI control button -> `pause_live_initiative`; text intent live -> `_runtime_control_intent` -> `_handle_runtime_control_intent`.
- suspend: UI control button -> `suspend_live_runtime_initiative`; text intent live -> `_runtime_control_intent` -> `_handle_runtime_control_intent`.
- unknown input: RC2 -> `local_model_consent_required` / provider preview / fallback `local_conversation_answer`; live fallback uses RC2 unless Wikipedia or governance intercepts.

## Override Points

- Old concept can override current topic: RC2 `query_approved_concepts`, `_last_concept_context`, `resolve_followup_anchor`, and `DeltaApp._update_active_topic_anchor` can steer follow-ups toward prior concept matches.
- Pending candidate can hijack ordinary turn: live `_is_affirmative` plus `_has_pending_promotion_inquiry`; UI pending local/provider/deepening blocks in `_send_chat`.
- Wikipedia can win: live `wikipedia_query_from_message` after governance/self-model/context checks and before RC2 fallback.
- Concept recall can win: RC2 explicit browse/multi-concept/WRS/concept memory branches precede final local conversation fallback.
- Local model reasoning can win: only after consent/approval or explicit `execute_local_model=True`.
- Follow-up state can be lost: short `DeltaApp._recent_history_for_router` window, active topic anchor based on payload, and history-derived anchors can diverge.
- Fallback can activate: inactive live runtime fallback, Wikipedia failure/budget exhausted, local-model unavailable, no concept match, provider unavailable/refused.
"""
    (OUT / "routing_execution_map.md").write_text(text, encoding="utf-8")


def write_static_reports(test_files: list[str]) -> None:
    (OUT / "routing_precedence.md").write_text(PRECEDENCE, encoding="utf-8")
    (OUT / "routing_state_map.md").write_text(STATE_MAP, encoding="utf-8")
    (OUT / "routing_risk_observations.md").write_text(RISK_REPORT, encoding="utf-8")
    lines = ["# Routing Test Inventory", ""]
    patterns = ["route_message", "handle_live_chat", "Wikipedia", "local_model", "greeting", "tell me more", "why", "pronoun", "pause", "suspend"]
    for item in test_files:
        text = (ROOT / item).read_text(encoding="utf-8", errors="ignore")
        covered = [pattern for pattern in patterns if pattern in text]
        assertions = [line.strip()[:220] for line in text.splitlines() if line.strip().startswith("assert ")]
        prompts = [phrase for phrase in ["hi", "hello", "tell me more", "why", "what do you mean", "Wikipedia", "pause", "suspend", "local model", "yes", "no"] if phrase in text]
        lines += [
            f"## `{item}`",
            f"File: `{item}`",
            f"Routes covered: {', '.join(covered) or 'inferred routing-adjacent'}",
            f"Important prompts: {', '.join(prompts) or 'not obvious from static scan'}",
            f"Assertions: {'; '.join(assertions[:8]) or 'No direct assert lines captured by static scan'}",
            f"Uses real runtime or fixture: {'real runtime API' if 'handle_live_chat' in text or 'route_message' in text else 'fixture or indirect'}",
            f"Uses fake Wikipedia: {'Yes' if 'wikipedia_transport' in text or 'fake' in text.lower() else 'No/unclear'}",
            f"Uses real local model: {'Possible' if 'ProviderManager' in text and 'fake' not in text.lower() else 'No/fixture/unclear'}",
            "Potential blind spots: Static inventory only; inspect individual tests before using coverage as proof of long-duration behavior.",
            "",
        ]
    (OUT / "routing_test_inventory.md").write_text("\n".join(lines), encoding="utf-8")


def write_source_bundle(files: list[str]) -> None:
    (OUT / "routing_source_files.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    for old in OUT.glob("routing_source_bundle*.md"):
        old.unlink()
    parts: list[str] = []
    current: list[str] = []
    size = 0
    max_size = 900_000
    for item in files:
        source = (ROOT / item).read_text(encoding="utf-8", errors="replace")
        block = "\n".join(["=" * 70, f"FILE: {item}", "=" * 70, "", source, ""])
        if current and size + len(block) > max_size:
            parts.append("\n".join(current))
            current = []
            size = 0
        current.append(block)
        size += len(block)
    if current:
        parts.append("\n".join(current))
    if len(parts) == 1:
        (OUT / "routing_source_bundle.md").write_text(parts[0], encoding="utf-8")
    else:
        for index, part in enumerate(parts, 1):
            (OUT / f"routing_source_bundle_{index:02d}.md").write_text(part, encoding="utf-8")


def write_manifest(files: list[str], tests: list[str]) -> dict[str, object]:
    manifest = {
        "repository": str(ROOT),
        "branch": BRANCH,
        "head": HEAD,
        "entry_point": "DELTA.py",
        "ui_submission_handler": "DELTA.py::DeltaApp._send_chat",
        "runtime_input_function": "orchestration/runtime/delta_1_4_live_wikipedia_runtime.py::handle_live_chat and orchestration/runtime/rc2_conversational_mode_router.py::route_message",
        "active_files": CATEGORIES["ACTIVE_RUNTIME"],
        "supporting_state_files": CATEGORIES["ACTIVE_SUPPORTING_STATE"],
        "retrieval_files": CATEGORIES["ACTIVE_RETRIEVAL"],
        "model_routing_files": [item for item in CATEGORIES["ACTIVE_MODEL_ROUTING"] if (ROOT / item).exists()],
        "governance_files": CATEGORIES["ACTIVE_GOVERNANCE"],
        "response_composition_files": CATEGORIES["ACTIVE_RESPONSE_COMPOSITION"],
        "test_files": tests,
        "dormant_or_obsolete_files": CATEGORIES["DORMANT_OR_OBSOLETE"],
        "uncertain_files": CATEGORIES["UNCERTAIN"],
        "routing_stages": ["UI _send_chat", "live handle_live_chat when active", "UI preemptions when non-live", "RC2 route_message", "route-specific handler", "render_route or LiveChatResponse.answer", "DeltaApp._append_chat"],
        "state_objects": ["session_history", "last_message", "last_payload", "active_topic_anchor", "pending_provider_question", "pending_local_model_question", "pending_local_model_deepening", "concept_review_items", "LiveWikipediaRuntimeSession", "continuous_controller", "operator_inquiries", "promotion_candidates", "pending_local_model_request", "autonomy_status", "model_residency", "route_arbitration", "cognitive_episode"],
        "observed_risks": ["RISK-001", "RISK-002", "RISK-003", "RISK-004", "RISK-005", "RISK-006", "RISK-007", "RISK-008", "RISK-009", "RISK-010"],
        "exported_source_file_count": len(files),
    }
    (OUT / "routing_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json.loads((OUT / "routing_manifest.json").read_text(encoding="utf-8"))
    return manifest


PRECEDENCE = """# Routing Precedence

## UI Precedence (`DELTA.py::DeltaApp._send_chat`)

| Priority | Condition | Selected route | File | Function | Can override | Can be overridden by | Fallback |
|---:|---|---|---|---|---|---|---|
| 1 | Empty message | No route | DELTA.py | `_send_chat` | Everything | None | Return |
| 2 | Live runtime active | Live runtime worker | DELTA.py | `_send_chat`, `_begin_live_runtime_turn` | All non-live UI/RC2 routes | None except queued lifecycle controls after worker completes | `handle_live_chat` |
| 3 | Render correction request | render correction payload | DELTA.py / rc2_render_correction.py | `_send_chat` | RC2 general routing | Live active | `route_message` render correction |
| 4 | Local report inspection | local report answer | DELTA.py | `_inspect_local_report` callers | RC2 routing | Live active/render correction | Continue |
| 5 | RC6 / RC45 / PC1 specialist shortcuts | fixed specialist answer | DELTA.py + rc45/pc1 modules | `_send_chat` preemption blocks | RC2 general routing | Earlier UI conditions | Continue |
| 6 | Pending local deepening affirmative/cancel | execute/cancel pending local deepening | DELTA.py | `_send_chat` | Ordinary turn meaning | Earlier UI conditions | Continue |
| 7 | Pending local model question affirmative/cancel | execute/cancel local model | DELTA.py | `_send_chat` | Ordinary affirmations | Earlier UI conditions | Continue |
| 8 | Pending provider question affirmative/cancel | approved provider preview/execution path | DELTA.py | `_send_chat` | Ordinary affirmations | Earlier UI conditions | Continue |
| 9 | Memory command | concept review candidate | DELTA.py | `_queue_last_answer_for_review` | RC2 routing | Earlier UI conditions | Continue |
| 10 | Default | RC2 route | DELTA.py / rc2_conversational_mode_router.py | `route_message` | None | Earlier UI conditions | render_route |

## Live Runtime Precedence (`handle_live_chat`)

| Priority | Condition | Selected route | File | Function | Can override | Can be overridden by | Fallback |
|---:|---|---|---|---|---|---|---|
| 1 | Session inactive | inactive fallback | delta_1_4_live_wikipedia_runtime.py | `handle_live_chat` | Live features | None | RC2 route/render |
| 2 | Lifecycle text intent | runtime control | delta_1_4_live_wikipedia_runtime.py | `_runtime_control_intent`, `_handle_runtime_control_intent` | Pending approvals/Wikipedia/fallback | Active session only | live state response |
| 3 | Autonomy suspended | suspended refusal | same | `handle_live_chat` | Retrieval/model/initiation | Lifecycle controls | response |
| 4 | Pending inquiry question | pending inquiries | same | `_is_pending_inquiry_question`, `_render_pending_inquiries` | Fallback | Lifecycle/suspend | response |
| 5 | Pending local request explicit cancel/approval | local model cancel/execute | same | `_has_pending_local_model_request`, `_run_approved_local_model_request` | Promotion/Wikipedia/fallback | Lifecycle/suspend/pause | response |
| 6 | Pending local + pending promotion + bare yes | ambiguous live action | same | `_render_ambiguous_live_action` | Accidental approval | explicit local request/cancel | response |
| 7 | Pending promotion affirmative/rejection | promotion approve/reject | same | `_approve_pending_promotion`, `_reject_pending_promotion` | Wikipedia/fallback | lifecycle/pause/ambiguity | response |
| 8 | Help/memory/self-model/context | governance or self-model response | same | `_is_live_help_request`, `_is_memory_request`, `is_operational_self_model_question`, `_is_live_context_declaration` | Wikipedia/fallback | pending approvals/lifecycle | response |
| 9 | Wikipedia query and budget | Wikipedia retrieval + developmental cognition | same | `wikipedia_query_from_message`, `retrieve_wikipedia_text` | RC2 fallback | pause/budget/failure | Wikipedia answer/failure |
| 10 | Default | RC2 fallback | same + rc2 router | `route_message`, `render_route` | None | earlier live routes | RC2 answer |

## RC2 Router Precedence (`route_message`)

RC2 precedence is implemented by early returns. In order: provider approval, GPT approval preview, social intent, render correction, clarification without history, early contradiction, execute-local-model route, early working-memory follow-up, development workflow, early analogy, early WRS, anchor follow-up, local model execution retry, direct/coding/external/image/development path, working-memory follow-up, knowledge browse, graph-assisted/synthesis/analogy/contradiction/WRS, multi-concept retrieval, domain browse, concept memory retrieval, mode-specific scaffold/fallback.
"""

STATE_MAP = """# Routing State Map

| State name | Defined in | Initialized in | Written by | Read by | Lifetime | Persisted or ephemeral | Clear/reset conditions | Potential stale-state risk |
|---|---|---|---|---|---|---|---|---|
| `session_history` | `DELTA.py::DeltaApp` | UI init | `_append_session` | `_recent_history_for_router`, `_send_chat` | UI process | Ephemeral | App restart; windowed by reader | Short window can omit older referents. |
| `last_message` | `DELTA.py::DeltaApp` | UI init | `_send_chat`, `_complete_live_runtime_turn` | `_queue_last_answer_for_review`, topic anchors | UI process | Ephemeral | New successful turn | Can point to transformed target prompt after approved local model. |
| `last_payload` | `DELTA.py::DeltaApp` | UI init | `_send_chat`, `_complete_live_runtime_turn` | concept review/memory commands | UI process | Ephemeral | New route payload | Can be stale if worker error occurs. |
| `active_topic_anchor` | `DELTA.py::DeltaApp` and RC2 payload | UI init | `_update_active_topic_anchor` | history/discourse route helpers | UI process | Ephemeral | New payload with anchor/matches | Old concept can steer later vague follow-ups. |
| `last_report_inspection` | `DELTA.py::DeltaApp` | UI init | local report inspection route | RC45 discourse shortcuts | UI process | Ephemeral | New report inspection | Report-specific preemptions can affect later ordinary language. |
| `pending_provider_question` | `DELTA.py::DeltaApp` | UI init | `_send_chat` | `_send_chat` approval blocks | Until approval/cancel/new route | Ephemeral | cancel/approve/route without offer | Bare yes may approve old provider request if not cleared. |
| `pending_local_model_question` | `DELTA.py::DeltaApp` | UI init | `_send_chat` | `_send_chat` approval blocks | Until approval/cancel/new route | Ephemeral | cancel/approve/local offer changes | Bare yes can execute older question. |
| `pending_local_model_deepening` | `DELTA.py::DeltaApp` | UI init | `_set_deepening_offer_if_present`, `_send_chat` | `_send_chat` | Until approval/cancel/default route | Ephemeral | cancel/approve/default route clears | `tell me more` can mean approval instead of conversation. |
| `concept_review_items` | `DELTA.py::DeltaApp` | UI init | `_queue_concept_candidate` | accept/reject/inspect buttons | UI process | Ephemeral until accepted | reject/accept/clear | Candidate tray can retain unrelated prior candidates. |
| `pending_live_runtime_controls` | `DELTA.py::DeltaApp` | UI init | `_queue_live_runtime_control` | `_apply_queued_live_runtime_controls` | While worker in flight | Ephemeral | worker completion | Control is delayed, so UI state can look ahead of runtime. |
| `LiveWikipediaRuntimeSession.active` | live runtime dataclass | `start_live_wikipedia_runtime` | start/stop | `handle_live_chat`, UI status | Live session | Ephemeral | stop | Inactive fallback skips live features. |
| `LiveWikipediaRuntimeSession.pending_local_model_request` | live runtime dataclass | `_new_local_model_request` | live fallback/local offer/cancel/execute | `handle_live_chat` | Live session | Ephemeral | cancel/execute/new unrelated fallback | Pending request competes with promotion inquiry. |
| `operator_inquiries` | live runtime dataclass/controller | Wikipedia developmental cognition/background cycles | live approval/rejection/cycles | `handle_live_chat`, status | Live session | Ephemeral | approval/rejection/stop | Multiple queued inquiries make bare approval ambiguous. |
| `promotion_candidates` | live runtime dataclass | Wikipedia developmental cognition/background cycles | live Wikipedia/self-model cycles | approval/memory gate/status | Live session | Ephemeral until accepted in UI | stop/restart | Latest candidate can influence unrelated memory requests. |
| `prepared_review_proposals` | live runtime dataclass | approval | `_approve_pending_promotion` | status/reporting | Live session | Ephemeral | stop/restart | Proposal presence may be mistaken for stored memory. |
| `autonomy_status` | live runtime dataclass | start | pause/resume/suspend | `handle_live_chat` | Live session | Ephemeral | resume/restart/stop | Paused/suspended state blocks routes until changed. |
| `continuous_controller` | live runtime dataclass | start | `_advance_continuous_controller`, pause/resume/suspend/shutdown | UI status/live decisions | Live session | Ephemeral | stop/shutdown | Controller/model state may diverge from UI provider manager. |
| `model_residency` | continuous controller/provider manager | runtime start/provider warm | `_record_local_model_residency`, UI warm | status/model selection | UI/live process | Ephemeral | model switch/unload/restart | This audit did not invoke or switch models. |
| `route_arbitration` | RC2 payload | `_finish_conversation_payload` | `build_route_arbitration_trace` | developer overlay/reports | Per turn | Ephemeral | next route | Trace records candidates but does not itself enforce all earlier UI/live precedence. |
| `cognitive_episode` | RC2 payload | `attach_episode` | RC2 route finish | developer overlay/follow-up | Per turn from history | Ephemeral | history truncation | Pronoun/referent confidence depends on recent rendered text. |
"""

RISK_REPORT = """# Routing Risk Observations

## RISK-001 Greeting Or Social Input Can Be Misrouted If Live Runtime Falls To RC2 After Pending State

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `handle_live_chat`
- relevant condition: pending local-model request, pending promotion inquiry, or runtime control checks run before RC2 fallback social classification.
- why it can produce the behavior: a bare `yes`, `tell me more`, or other short ordinary continuation can be consumed as approval/ambiguity before social/follow-up routing.
- confidence: confirmed by source precedence.

## RISK-002 Follow-Ups Can Lose Current Topic When History Window Or Anchor Diverges

- file: `DELTA.py`
- function: `_recent_history_for_router`, `_update_active_topic_anchor`
- relevant condition: routing receives only recent history, while UI also stores a separate active topic anchor from concept matches.
- why it can produce the behavior: RC2 follow-up resolution and UI anchor state are duplicated; a vague follow-up may resolve from rendered history, active anchor, or concept matches depending route order.
- confidence: confirmed by source structure.

## RISK-003 Old Concept Attractor Can Override Current Topic

- file: `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `_last_concept_context`, `resolve_followup_anchor`, `query_approved_concepts` branch in `route_message`
- relevant condition: history-derived concept names and approved concept retrieval run before final local conversation fallback.
- why it can produce the behavior: if a prior answer exposed concept names, follow-up/browse logic can continue those concepts even when the new prompt is underspecified.
- confidence: likely; source shows mechanism, behavioral frequency requires transcript evidence.

## RISK-004 Raw Prompts Can Become Wikipedia Page Titles

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `wikipedia_query_from_message`, `retrieve_wikipedia_text`
- relevant condition: messages matching `Wikipedia: topic`, `look up ... on Wikipedia`, or related forms are cleaned and sent to the REST summary endpoint.
- why it can produce the behavior: query construction is deterministic string extraction; ambiguous or over-broad user wording becomes the page query unless cleaned by `_clean_query`.
- confidence: confirmed by source.

## RISK-005 Wikipedia Can Preempt Local RC2 Reasoning In Live Mode

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `handle_live_chat`
- relevant condition: after governance/self-model/context checks, a recognized Wikipedia query retrieves before RC2 fallback.
- why it can produce the behavior: live Wikipedia routing is ordered before `route_message` fallback, so a prompt containing a lookup form will not first attempt local reasoning.
- confidence: confirmed.

## RISK-006 Stale Pending Approvals Can Hijack Later Turns

- file: `DELTA.py`
- function: `_send_chat`
- relevant condition: `pending_provider_question`, `pending_local_model_question`, and `pending_local_model_deepening` are checked before default RC2 routing.
- why it can produce the behavior: ordinary affirmations or `tell me more` can execute/cancel pending actions from a prior turn if the pending field remains set.
- confidence: confirmed by source precedence.

## RISK-007 Local-Model Warmup Failure Falls Back Into Consent/Provider Paths

- file: `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `execute_local_model_answer`, `local_conversation_answer`
- relevant condition: local inference failures return `executed=False` with a reason; later logic may offer provider/support or local consent depending route.
- why it can produce the behavior: model failure is represented as payload state rather than exception; user-facing answer may become unavailable/support-offer instead of direct model error.
- confidence: likely.

## RISK-008 Self-Model State Can Lag Provider Residency

- file: `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`
- function: `_record_local_model_residency`, `_provider_residency_status`; `answer_operational_self_model_question`
- relevant condition: controller model residency is updated after approved local-model calls and status is sampled from provider manager.
- why it can produce the behavior: if provider manager status fails or a UI-side warm/switch happened outside the live controller, self-model/status can disagree with real residency.
- confidence: possible.

## RISK-009 Response Composition Uses Multiple Independent Frames

- file: `DELTA.py`, `orchestration/runtime/rc2_conversational_mode_router.py`, `orchestration/runtime/rc2_cognitive_episode.py`
- function: `_send_chat`, `_finish_conversation_payload`, `attach_episode`
- relevant condition: UI discourse frame, RC2 route arbitration, and cognitive episode are separate analyses of the same message/history.
- why it can produce the behavior: developer overlay or preemptive UI route may describe one frame while the payload/rendered response follows another.
- confidence: confirmed by source structure.

## RISK-010 Conflicting Route Precedence Across UI, Live Runtime, And RC2

- file: `DELTA.py`, `orchestration/runtime/delta_1_4_live_wikipedia_runtime.py`, `orchestration/runtime/rc2_conversational_mode_router.py`
- function: `_send_chat`, `handle_live_chat`, `route_message`
- relevant condition: each layer has its own early-return precedence.
- why it can produce the behavior: a prompt can be social in RC2, approval in UI, lifecycle in live mode, or Wikipedia in live mode depending active session and pending fields.
- confidence: confirmed.
"""


def main() -> None:
    files = existing_files()
    tests = discover_tests()
    write_inventory()
    write_execution_map()
    write_static_reports(tests)
    write_source_bundle(files)
    manifest = write_manifest(files, tests)
    artifacts = sorted(path.name for path in OUT.iterdir())
    print("ROUTING EXPORT COMPLETE")
    print()
    print(f"Branch: {BRANCH}")
    print(f"HEAD: {HEAD}")
    print("Active entry point: DELTA.py")
    print("UI submission handler: DELTA.py::DeltaApp._send_chat")
    print("Runtime input function: delta_1_4_live_wikipedia_runtime.handle_live_chat / rc2_conversational_mode_router.route_message")
    print(f"Active routing files: {len(CATEGORIES['ACTIVE_RUNTIME'])}")
    print(f"Supporting state files: {len(CATEGORIES['ACTIVE_SUPPORTING_STATE'])}")
    print(f"Retrieval files: {len(CATEGORIES['ACTIVE_RETRIEVAL'])}")
    print(f"Model-routing files: {len(manifest['model_routing_files'])}")
    print(f"Governance files: {len(CATEGORIES['ACTIVE_GOVERNANCE'])}")
    print(f"Response-composition files: {len(CATEGORIES['ACTIVE_RESPONSE_COMPOSITION'])}")
    print(f"Routing test files: {len(tests)}")
    print(f"Dormant/obsolete files: {len(CATEGORIES['DORMANT_OR_OBSOLETE'])}")
    print(f"Uncertain files: {len(CATEGORIES['UNCERTAIN'])}")
    print()
    print("Artifacts created:")
    for artifact in artifacts:
        print(f"- {artifact}")


if __name__ == "__main__":
    main()
