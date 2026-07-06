from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_operator_console import (  # noqa: E402
    append_observation,
    answer_operator_question,
    approve_propositions,
    build_observation_entry,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    validate_console_safe,
)
from orchestration.runtime.rc2_conversational_mode_router import MODES, render_route, route_message  # noqa: E402


def _format_snapshot(snapshot: dict[str, object]) -> str:
    status = snapshot["runtime_status"]
    corpus = snapshot["corpus_substrate"]
    replay = snapshot["replay_rollback"]
    queue = snapshot["operator_review_queue"]
    lines = [
        "DELTA Runtime v4.0 RC1 Operator Console",
        "",
        f"Version: {status['version']}",
        f"Status: {status['status']}",
        f"Operational baseline: {status['operational_baseline']}",
        f"Latest TP phase: {status['latest_tp_phase']}",
        f"Latest recommendation: {status['latest_tp_recommendation']}",
        "",
        "Corpus / substrate:",
        f"- substrate improvements: {corpus['substrate_improvement_count']}",
        f"- canonical writes enabled: {corpus['canonical_write_enabled']}",
        f"- training enabled: {corpus['training_enabled']}",
        "",
        "Review / replay:",
        f"- review queue references: {len(queue)}",
        f"- rollback records: {replay['rollback_records']}",
        f"- replay report available: {replay['replay_report_available']}",
        "",
        "Safety:",
    ]
    safety = status["safety"]
    for key in [
        "provider_calls_enabled",
        "training_enabled",
        "canonical_writes_enabled",
        "autonomous_actions_enabled",
        "scheduler_enabled",
        "hyb1_promoted",
        "model_b_default_changed",
    ]:
        if key in safety:
            lines.append(f"- {key}: {safety[key]}")
    return "\n".join(lines)


def _format_cognitive_state(state: dict[str, object]) -> str:
    lines = [
        "Cognitive State",
        "",
        f"Knowledge available: {state['knowledge_available']}",
        f"Noncanonical propositions: {state['noncanonical_propositions']}",
        f"Evidence links: {state['evidence_links']}",
        f"Concepts: {state['concepts']}",
        f"Contradictions: {state['contradictions']}",
        f"Pending review: {state['pending_review']}",
        f"Replay queue: {state['replay_queue']}",
        f"Canonical records: {state['canonical_records']}",
        "",
        "Operational rhythm:",
        "1. Paste evidence.",
        "2. Extract propositions.",
        "3. Review and approve noncanonical records.",
        "4. Ask questions against approved evidence.",
        "5. Log failures or friction.",
    ]
    return "\n".join(lines)


class DeltaOperatorConsole:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DELTA RC1 Operator Console")
        self.root.geometry("1120x760")
        self.snapshot = build_operator_snapshot()
        self.extracted: list[dict[str, object]] = []
        if not validate_console_safe(self.snapshot):
            raise RuntimeError("RC1 operator console safety validation failed")
        self._build()
        self._show_status()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.LabelFrame(frame, text="Cognitive State")
        header.pack(fill=tk.X)
        self.state_vars: dict[str, tk.StringVar] = {}
        state_fields = [
            ("Knowledge", "knowledge_available"),
            ("Propositions", "noncanonical_propositions"),
            ("Evidence", "evidence_links"),
            ("Concepts", "concepts"),
            ("Contradictions", "contradictions"),
            ("Pending", "pending_review"),
            ("Replay", "replay_queue"),
        ]
        for index, (label, key) in enumerate(state_fields):
            card = ttk.Frame(header, padding=6)
            card.grid(row=0, column=index, sticky="ew")
            header.columnconfigure(index, weight=1)
            ttk.Label(card, text=label).pack()
            self.state_vars[key] = tk.StringVar(value="-")
            ttk.Label(card, textvariable=self.state_vars[key], font=("Segoe UI", 11, "bold")).pack()

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(actions, text="Import / Paste", command=self._focus_import).pack(side=tk.LEFT)
        ttk.Button(actions, text="Extract", command=self._extract_propositions).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Approve", command=self._approve_extracted).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Ask", command=self._ask).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Replay", command=self._show_replay).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(actions, text="Log Issue", command=self._log_observation).pack(side=tk.LEFT, padx=(6, 0))

        ask_bar = ttk.LabelFrame(frame, text="DELTA Conversation / Mode Router")
        ask_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(ask_bar, text="Mode").pack(side=tk.LEFT, padx=(6, 0))
        self.mode = ttk.Combobox(ask_bar, values=MODES, width=24, state="readonly")
        self.mode.set("Conversation")
        self.mode.pack(side=tk.LEFT, padx=6, pady=6)
        self.question = ttk.Entry(ask_bar)
        self.question.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=6)
        self.question.insert(0, "What color is the sky?")
        ttk.Button(ask_bar, text="Send", command=self._ask).pack(side=tk.RIGHT, padx=6)

        panes = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)

        ttk.Label(left, text="Import / Paste Evidence").pack(anchor=tk.W)
        self.paste = scrolledtext.ScrolledText(left, height=12, wrap=tk.WORD)
        self.paste.pack(fill=tk.BOTH, expand=True)
        ttk.Button(left, text="Preview Evidence", command=self._preview_evidence).pack(fill=tk.X, pady=(6, 0))
        ttk.Button(left, text="Extract Propositions", command=self._extract_propositions).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(left, text="Approve Extracted To Noncanonical Substrate", command=self._approve_extracted).pack(fill=tk.X, pady=(4, 0))

        obs = ttk.LabelFrame(left, text="Operational Observation")
        obs.pack(fill=tk.X, pady=(10, 0))
        self.category = ttk.Combobox(
            obs,
            values=[
                "operator_friction",
                "missing_evidence",
                "confusing_behavior",
                "weak_explanation",
                "replay_problem",
                "retrieval_failure",
                "provenance_issue",
                "latency",
                "workflow_interruption",
                "feature_request",
                "unexpected_strength",
            ],
        )
        self.category.set("operator_friction")
        self.category.pack(fill=tk.X, padx=6, pady=4)
        self.severity = ttk.Combobox(obs, values=["P0", "P1", "P2", "P3"])
        self.severity.set("P3")
        self.severity.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(obs, text="Log Observation Locally", command=self._log_observation).pack(fill=tk.X, padx=6, pady=6)

        buttons = ttk.Frame(left)
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(buttons, text="Status", command=self._show_status).pack(fill=tk.X)
        ttk.Button(buttons, text="Cognitive State", command=self._show_cognitive_state).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Review Queue", command=self._show_review_queue).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Replay / Rollback", command=self._show_replay).pack(fill=tk.X, pady=(4, 0))
        ttk.Button(buttons, text="Failure Taxonomy", command=self._show_failure_taxonomy).pack(fill=tk.X, pady=(4, 0))

        ttk.Label(right, text="Workspace").pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.output.pack(fill=tk.BOTH, expand=True)

        self.question.bind("<Return>", lambda _event: self._ask())
        self._refresh_state_cards()

    def _write_output(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

    def _refresh_state_cards(self) -> None:
        state = build_cognitive_state()
        for key, var in self.state_vars.items():
            var.set(str(state[key]))

    def _focus_import(self) -> None:
        self.paste.focus_set()
        self._write_output(
            "Paste evidence on the left, then use Extract Propositions. "
            "Nothing becomes available for reasoning until you approve extracted propositions into the RC1 noncanonical substrate."
        )

    def _ask(self) -> None:
        message = self.question.get().strip()
        if not message:
            return
        data = route_message(self.mode.get(), message, self.paste.get("1.0", tk.END))
        self._refresh_state_cards()
        self._write_output(render_route(data))

    def _preview_evidence(self) -> None:
        data = preview_evidence_ingest(self.paste.get("1.0", tk.END))
        self._refresh_state_cards()
        self._write_output(json.dumps(data, indent=2, sort_keys=True))

    def _extract_propositions(self) -> None:
        data = extract_propositions(self.paste.get("1.0", tk.END))
        self.extracted = data["candidates"]
        self._refresh_state_cards()
        lines = ["Detected Propositions", ""]
        if not self.extracted:
            lines.append("No proposition candidates detected.")
        for idx, item in enumerate(self.extracted, start=1):
            lines.append(f"[x] {idx}. {item['claim']}")
            lines.append(f"    id: {item['proposition_id']}")
            lines.append(f"    source: {item['source']}")
            lines.append(f"    confidence: {item['confidence']}")
        lines.extend([
            "",
            "Nothing has been persisted yet.",
            "Click 'Approve Extracted To Noncanonical Substrate' to create local RC1 noncanonical records.",
        ])
        self._write_output("\n".join(lines))

    def _approve_extracted(self) -> None:
        if not self.extracted:
            self._extract_propositions()
        result = approve_propositions(self.extracted)
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(json.dumps(result, indent=2, sort_keys=True))

    def _log_observation(self) -> None:
        note = self.paste.get("1.0", tk.END).strip()
        if not note:
            note = "Operator created an empty observation placeholder from the RC1 console."
        entry = build_observation_entry(self.category.get(), note, self.severity.get())
        result = append_observation(entry)
        self._refresh_state_cards()
        self._write_output(json.dumps({"entry": entry, "result": result}, indent=2, sort_keys=True))

    def _show_status(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        self._write_output(_format_snapshot(self.snapshot))

    def _show_cognitive_state(self) -> None:
        state = build_cognitive_state()
        self._refresh_state_cards()
        self._write_output(_format_cognitive_state(state))

    def _show_review_queue(self) -> None:
        self._write_output(json.dumps(self.snapshot["operator_review_queue"], indent=2, sort_keys=True))

    def _show_replay(self) -> None:
        self._write_output(json.dumps(self.snapshot["replay_rollback"], indent=2, sort_keys=True))

    def _show_failure_taxonomy(self) -> None:
        self._write_output(json.dumps(self.snapshot["failure_classification"], indent=2, sort_keys=True))


def main() -> int:
    root = tk.Tk()
    DeltaOperatorConsole(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
