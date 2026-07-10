from __future__ import annotations

import json
import uuid
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, simpledialog, ttk


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc1_operator_console import (  # noqa: E402
    append_observation,
    approve_propositions,
    build_observation_entry,
    build_cognitive_state,
    build_operator_snapshot,
    extract_propositions,
    preview_evidence_ingest,
    validate_console_safe,
)
from orchestration.runtime.rc2_developmental_concept_memory import (  # noqa: E402
    approve_candidate_concept,
    build_developmental_memory_state,
    clear_developmental_memory_store,
    query_approved_concepts,
)
from orchestration.runtime.rc2_conversational_mode_router import (  # noqa: E402
    DISPLAY_MODES,
    build_memory_candidate_from_answer,
    candidate_is_memory_worthy,
    render_route,
    route_message,
    select_model_lane,
)
from orchestration.runtime.rc2_storage_adapter import backend_health, load_diverse_concepts, search_concepts, substrate_counts  # noqa: E402
from orchestration.runtime.rc2_substrate_reconciliation import build_substrate_reconciliation  # noqa: E402
from orchestration.runtime.rc3_ui_capability_adapter import (  # noqa: E402
    PANEL_ORDER,
    build_rc3_ui_integration_report,
    build_rc3_ui_snapshot,
    render_rc3_panel,
    validate_rc3_ui_snapshot,
)
from integration.model_runtime.provider_manager import ProviderManager  # noqa: E402


def _format_cognitive_state(state: dict[str, object]) -> str:
    return "\n".join([
        "Cognitive State",
        "",
        f"Knowledge available: {state['knowledge_available']}",
        f"Noncanonical propositions: {state['noncanonical_propositions']}",
        f"Evidence links: {state['evidence_links']}",
        f"Active runtime concepts: {state['concepts']}",
        f"Contradictions: {state['contradictions']}",
        f"Pending review: {state['pending_review']}",
        f"Substrate replay events: {state['replay_queue']}",
        f"Migration audit events: {state.get('migration_audit_events', 0)}",
        f"Canonical records: {state['canonical_records']}",
    ])


def _format_snapshot(snapshot: dict[str, object]) -> str:
    status = snapshot["runtime_status"]
    corpus = snapshot["corpus_substrate"]
    replay = snapshot["replay_rollback"]
    queue = snapshot["operator_review_queue"]
    backend = backend_health()
    counts = substrate_counts()
    reconciliation = counts.get("reconciliation") or build_substrate_reconciliation(write_reports=False)
    developmental = build_developmental_memory_state()
    return "\n".join([
        "DELTA Advanced Operator Console",
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
        "Storage backend:",
        f"- backend: {backend.get('backend')}",
        f"- sqlite available: {backend.get('sqlite_available')}",
        f"- sqlite fresh: {backend.get('fresh')}",
        f"- active runtime concepts: {counts.get('active_runtime_concepts', counts.get('concepts'))}",
        f"- active graph edges: {counts.get('active_graph_edges', counts.get('graph_edges'))}",
        f"- substrate replay events: {counts.get('substrate_replay_events', counts.get('replay_events'))}",
        f"- concept replay events: {counts.get('concept_replay_events')}",
        f"- graph edge replay events: {counts.get('graph_edge_replay_events')}",
        f"- migration audit events: {counts.get('migration_audit_events')}",
        f"- legacy JSONL concepts: {counts.get('legacy_jsonl_concepts')}",
        f"- legacy JSONL graph edges: {counts.get('legacy_jsonl_graph_edges')}",
        f"- developmental memory records: {developmental.get('knowledge_memory_records')}",
        f"- concept import coverage: {counts.get('concept_replay_coverage')}",
        f"- edge import coverage: {counts.get('edge_replay_coverage')}",
        f"- authoritative concept counter: {reconciliation.get('authoritative_runtime_concept_counter')}",
    ])


def _model_answer_offers_deepening(answer: str) -> bool:
    lower = " ".join(str(answer or "").lower().split())
    offers = (
        "would you like me to explore",
        "would you like me to go deeper",
        "would you like more detail",
        "would you like more details",
        "would you like examples",
        "should i go deeper",
        "do you want me to expand",
        "want me to expand",
    )
    return any(phrase in lower for phrase in offers)


def _build_deepening_prompt(question: str, prior_answer: str) -> str:
    return (
        "Please expand on your previous answer for this user question.\n\n"
        f"Original question: {question}\n\n"
        f"Previous answer: {prior_answer}\n\n"
        "Go deeper, add useful nuance, keep it conversational, and do not ask to store memory."
    )


def _assistant_answer_text(content: str) -> str:
    text = str(content or "")
    return text.split("--- Developer Overlay ---", 1)[0].strip()


def _lines_from_text(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


class DeltaApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DELTA Cognitive OS")
        self.root.geometry("1180x700")
        self.root.minsize(960, 620)
        self.snapshot = build_operator_snapshot()
        self.extracted: list[dict[str, object]] = []
        self.last_message = ""
        self.last_payload: dict[str, object] | None = None
        self.concept_review_items: dict[str, dict[str, object]] = {}
        self.session_history: list[dict[str, str]] = []
        self.pending_provider_question: str | None = None
        self.pending_local_model_question: str | None = None
        self.pending_local_model_deepening: dict[str, str] | None = None
        self.active_topic_anchor: dict[str, object] | None = None
        self.provider_manager = ProviderManager(keep_loaded=True)
        self.resident_model_id: str | None = None
        self.resident_lane: str | None = None
        self.model_residency_status = "not_warmed"
        self.developer_overlay_enabled = tk.BooleanVar(value=False)
        if not validate_console_safe(self.snapshot):
            raise RuntimeError("DELTA console safety validation failed")
        self._build()
        self._refresh_state_cards()
        self._warm_default_model()
        self._show_welcome()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.conversation_tab = ttk.Frame(self.notebook, padding=10)
        self.database_tab = ttk.Frame(self.notebook, padding=10)
        self.rc3_tab = ttk.Frame(self.notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.conversation_tab, text="Conversation")
        self.notebook.add(self.database_tab, text="Database")
        self.notebook.add(self.rc3_tab, text="RC3")
        self.notebook.add(self.advanced_tab, text="Advanced / Operator Console")

        self._build_conversation_tab()
        self._build_database_tab()
        self._build_rc3_tab()
        self._build_advanced_tab()

    def _build_conversation_tab(self) -> None:
        header = ttk.LabelFrame(self.conversation_tab, text="Cognitive State")
        header.pack(fill=tk.X)
        self.state_vars: dict[str, tk.StringVar] = {}
        for index, (label, key) in enumerate([
            ("Knowledge", "knowledge_available"),
            ("Propositions", "noncanonical_propositions"),
            ("Evidence", "evidence_links"),
            ("Active concepts", "concepts"),
            ("Contradictions", "contradictions"),
            ("Replay / audit", "replay_queue"),
            ("Migration audit", "migration_audit_events"),
        ]):
            card = ttk.Frame(header, padding=6)
            card.grid(row=0, column=index, sticky="ew")
            header.columnconfigure(index, weight=1)
            ttk.Label(card, text=label).pack()
            self.state_vars[key] = tk.StringVar(value="-")
            ttk.Label(card, textvariable=self.state_vars[key], font=("Segoe UI", 11, "bold")).pack()

        mode_bar = ttk.Frame(self.conversation_tab)
        mode_bar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(mode_bar, text="Mode").pack(side=tk.LEFT)
        self.mode = ttk.Combobox(mode_bar, values=DISPLAY_MODES, width=22, state="readonly")
        self.mode.set("Conversation")
        self.mode.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Checkbutton(mode_bar, text="Developer Overlay", variable=self.developer_overlay_enabled).pack(side=tk.LEFT)
        ttk.Button(mode_bar, text="Advanced Operator Console", command=lambda: self.notebook.select(self.advanced_tab)).pack(side=tk.RIGHT)

        self.chat_history = scrolledtext.ScrolledText(self.conversation_tab, wrap=tk.WORD, height=24)
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.chat_history.configure(state=tk.DISABLED)

        input_bar = ttk.Frame(self.conversation_tab)
        input_bar.pack(fill=tk.X, pady=(8, 0))
        self.chat_input = ttk.Entry(input_bar)
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.chat_input.insert(0, "What color is the sky?")
        ttk.Button(input_bar, text="Send", command=self._send_chat).pack(side=tk.RIGHT)
        self.chat_input.bind("<Return>", lambda _event: self._send_chat())

        memory_bar = ttk.Frame(self.conversation_tab)
        memory_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(memory_bar, text="Accept Selected Concept", command=self._accept_selected_concept).pack(side=tk.LEFT)
        ttk.Button(memory_bar, text="Reject Selected Concept", command=self._reject_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Inspect Selected Concept", command=self._inspect_selected_concept).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Clear Local Memory Store", command=self._clear_local_store).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(memory_bar, text="Open Operator Console", command=lambda: self.notebook.select(self.advanced_tab)).pack(side=tk.RIGHT)

        review = ttk.LabelFrame(self.conversation_tab, text="Concept Review")
        review.pack(fill=tk.X, pady=(8, 0))
        self.concept_review = ttk.Treeview(review, columns=("concept", "source", "status"), show="headings", height=3)
        self.concept_review.heading("concept", text="Potential Concept")
        self.concept_review.heading("source", text="Source")
        self.concept_review.heading("status", text="Status")
        self.concept_review.column("concept", width=360)
        self.concept_review.column("source", width=180)
        self.concept_review.column("status", width=120)
        self.concept_review.pack(fill=tk.X, padx=6, pady=6)

        hint = ttk.Label(
            self.conversation_tab,
            text="Default mode is natural conversation. Possible concepts appear in Concept Review and are stored only if you press Accept.",
        )
        hint.pack(anchor=tk.W, pady=(6, 0))

    def _build_database_tab(self) -> None:
        top = ttk.Frame(self.database_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Concept Lookup").pack(side=tk.LEFT)
        self.database_query = ttk.Entry(top)
        self.database_query.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.database_query.bind("<Return>", lambda _event: self._search_database_concepts())
        ttk.Button(top, text="Search", command=self._search_database_concepts).pack(side=tk.LEFT)
        ttk.Button(top, text="Browse Diverse", command=self._load_database_concepts).pack(side=tk.LEFT, padx=(8, 0))

        self.database_status = tk.StringVar(value="Read-only concept database.")
        ttk.Label(self.database_tab, textvariable=self.database_status).pack(anchor=tk.W, pady=(8, 0))

        page_bar = ttk.Frame(self.database_tab)
        page_bar.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(page_bar, text="Previous", command=self._database_previous_page).pack(side=tk.LEFT)
        ttk.Button(page_bar, text="Next", command=self._database_next_page).pack(side=tk.LEFT, padx=(8, 0))
        self.database_page_status = tk.StringVar(value="")
        ttk.Label(page_bar, textvariable=self.database_page_status).pack(side=tk.LEFT, padx=(12, 0))

        panes = ttk.PanedWindow(self.database_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        list_frame = ttk.Frame(panes)
        detail_frame = ttk.Frame(panes)
        panes.add(list_frame, weight=3)
        panes.add(detail_frame, weight=2)

        self.database_concepts = ttk.Treeview(
            list_frame,
            columns=("name", "domain", "type", "quality"),
            show="headings",
            height=18,
        )
        self.database_concepts.heading("name", text="Concept")
        self.database_concepts.heading("domain", text="Domain")
        self.database_concepts.heading("type", text="Type")
        self.database_concepts.heading("quality", text="Quality")
        self.database_concepts.column("name", width=320)
        self.database_concepts.column("domain", width=160)
        self.database_concepts.column("type", width=220)
        self.database_concepts.column("quality", width=80, anchor=tk.CENTER)
        self.database_concepts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.database_concepts.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.database_concepts.configure(yscrollcommand=scrollbar.set)
        self.database_concepts.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_database_concept())

        ttk.Label(detail_frame, text="Concept Detail").pack(anchor=tk.W)
        self.database_detail = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD)
        self.database_detail.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.database_detail.configure(state=tk.DISABLED)
        self.database_items: dict[str, dict[str, object]] = {}
        self.database_results: list[dict[str, object]] = []
        self.database_page = 0
        self.database_page_size = 100
        self.database_result_status = ""
        self._load_database_concepts()

    def _build_rc3_tab(self) -> None:
        top = ttk.Frame(self.rc3_tab)
        top.pack(fill=tk.X)
        ttk.Label(top, text="RC3 Capability Panels").pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self._refresh_rc3_snapshot).pack(side=tk.RIGHT)
        ttk.Button(top, text="Generate UI Report", command=self._generate_rc3_ui_report).pack(side=tk.RIGHT, padx=(0, 8))

        self.rc3_status = tk.StringVar(value="Read-only RC3 diagnostics. No execution controls are available.")
        ttk.Label(self.rc3_tab, textvariable=self.rc3_status).pack(anchor=tk.W, pady=(8, 0))

        panes = ttk.PanedWindow(self.rc3_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        self.rc3_panels = ttk.Treeview(left, columns=("status",), show="headings", height=18)
        self.rc3_panels.heading("status", text="Panel")
        self.rc3_panels.column("status", width=240)
        self.rc3_panels.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.rc3_panels.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rc3_panels.configure(yscrollcommand=scrollbar.set)
        self.rc3_panels.bind("<<TreeviewSelect>>", lambda _event: self._show_selected_rc3_panel())

        self.rc3_detail = scrolledtext.ScrolledText(right, wrap=tk.WORD)
        self.rc3_detail.pack(fill=tk.BOTH, expand=True)
        self.rc3_detail.configure(state=tk.DISABLED)
        self.rc3_snapshot: dict[str, object] = {}
        self._refresh_rc3_snapshot()

    def _build_advanced_tab(self) -> None:
        panes = ttk.PanedWindow(self.advanced_tab, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
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

    def _refresh_rc3_snapshot(self) -> None:
        try:
            self.rc3_snapshot = build_rc3_ui_snapshot()
            validation = validate_rc3_ui_snapshot(self.rc3_snapshot)
            for item in self.rc3_panels.get_children():
                self.rc3_panels.delete(item)
            panels = self.rc3_snapshot.get("panels", {})
            for name in PANEL_ORDER:
                panel = panels.get(name, {}) if isinstance(panels, dict) else {}
                status = str(panel.get("status", "unknown"))
                self.rc3_panels.insert("", tk.END, iid=name, values=(f"{name} [{status}]",))
            recommendation = validation.get("recommendation")
            self.rc3_status.set(
                f"RC3 UI validation passed={validation.get('passed')}; recommendation={recommendation}. "
                "Inspect/review only: no execution, sandbox, plugin activation, provider call, or repository mutation."
            )
            if PANEL_ORDER:
                self.rc3_panels.selection_set(PANEL_ORDER[0])
                self._show_selected_rc3_panel()
        except Exception as exc:  # noqa: BLE001
            self.rc3_status.set(f"RC3 snapshot failed: {type(exc).__name__}: {str(exc)[:180]}")
            self._write_rc3_detail("")

    def _show_selected_rc3_panel(self) -> None:
        selected = self.rc3_panels.selection()
        if not selected or not self.rc3_snapshot:
            return
        panel_name = str(selected[0])
        self._write_rc3_detail(render_rc3_panel(panel_name, self.rc3_snapshot))

    def _write_rc3_detail(self, text: str) -> None:
        self.rc3_detail.configure(state=tk.NORMAL)
        self.rc3_detail.delete("1.0", tk.END)
        if text:
            self.rc3_detail.insert(tk.END, text)
        self.rc3_detail.configure(state=tk.DISABLED)

    def _generate_rc3_ui_report(self) -> None:
        report = build_rc3_ui_integration_report(write_reports=True)
        self._refresh_rc3_snapshot()
        self._write_rc3_detail(json.dumps(report, indent=2, sort_keys=True))

    def _refresh_state_cards(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        substrate = substrate_counts()
        active_concepts = int(substrate.get("active_runtime_concepts", substrate.get("concepts", 0)) or 0)
        replay_events = int(substrate.get("substrate_replay_events", substrate.get("replay_events", 0)) or 0)
        state = {
            **state,
            "knowledge_available": state["knowledge_available"] or developmental["knowledge_memory_records"] > 0 or active_concepts > 0,
            "concepts": active_concepts,
            "contradictions": state["contradictions"] + developmental["concept_contradictions"],
            "replay_queue": replay_events,
            "migration_audit_events": int(substrate.get("migration_audit_events", 0) or 0),
        }
        for key, var in self.state_vars.items():
            var.set(str(state[key]))

    def _load_database_concepts(self) -> None:
        try:
            concepts = load_diverse_concepts(limit=1000)
            self._set_database_results(
                concepts,
                f"Showing diversified concepts from {substrate_counts().get('backend')} backend.",
            )
        except Exception as exc:  # noqa: BLE001 - UI should remain open if index is unavailable.
            self._set_database_results([], f"Database lookup failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _search_database_concepts(self) -> None:
        query = self.database_query.get().strip()
        if not query:
            self._load_database_concepts()
            return
        try:
            result = search_concepts(query, limit=1000)
            concepts = result.get("matches", [])
            backend = result.get("backend") or substrate_counts().get("backend")
            self._set_database_results(
                concepts,
                f"Search `{query}`: {len(concepts)} result(s), backend={backend}, candidate_pool={result.get('candidate_pool_size', 'n/a')}.",
            )
        except Exception as exc:  # noqa: BLE001
            self._set_database_results([], f"Search failed: {type(exc).__name__}: {str(exc)[:160]}")

    def _set_database_results(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_results = list(concepts)
        self.database_page = 0
        self.database_result_status = status
        self._show_database_page()

    def _database_next_page(self) -> None:
        if (self.database_page + 1) * self.database_page_size >= len(self.database_results):
            return
        self.database_page += 1
        self._show_database_page()

    def _database_previous_page(self) -> None:
        if self.database_page <= 0:
            return
        self.database_page -= 1
        self._show_database_page()

    def _show_database_page(self) -> None:
        start = self.database_page * self.database_page_size
        end = start + self.database_page_size
        self._populate_database_concepts(self.database_results[start:end], self.database_result_status)
        total = len(self.database_results)
        if total:
            self.database_page_status.set(f"Showing {start + 1}-{min(end, total)} of {total}")
        else:
            self.database_page_status.set("No concepts to show")

    def _populate_database_concepts(self, concepts: list[dict[str, object]], status: str) -> None:
        self.database_items = {}
        for item in self.database_concepts.get_children():
            self.database_concepts.delete(item)
        for concept in concepts:
            concept_id = str(concept.get("concept_id") or "")
            if not concept_id:
                continue
            self.database_items[concept_id] = concept
            quality = concept.get("quality_score", concept.get("confidence", ""))
            self.database_concepts.insert(
                "",
                tk.END,
                iid=concept_id,
                values=(
                    str(concept.get("concept_name") or ""),
                    str(concept.get("domain") or ""),
                    str(concept.get("concept_type") or ""),
                    str(quality)[:8],
                ),
            )
        counts = substrate_counts()
        self.database_status.set(
            f"{status} Active concepts={counts.get('active_runtime_concepts', counts.get('concepts'))}; "
            f"active graph edges={counts.get('active_graph_edges', counts.get('graph_edges'))}; "
            f"replay events={counts.get('substrate_replay_events', counts.get('replay_events'))}."
        )
        self._write_database_detail("")

    def _show_selected_database_concept(self) -> None:
        selected = self.database_concepts.selection()
        if not selected:
            return
        concept = self.database_items.get(str(selected[0]))
        if not concept:
            return
        lines = [
            str(concept.get("concept_name") or "Unnamed Concept"),
            "",
            f"ID: {concept.get('concept_id')}",
            f"Domain: {concept.get('domain')}",
            f"Type: {concept.get('concept_type')}",
            f"Quality: {concept.get('quality_score', concept.get('confidence', ''))}",
            f"Status: {concept.get('approval_status')}",
            f"Canonical: {concept.get('canonical')}",
            f"Source: {concept.get('source_type') or concept.get('_store_memory_type') or ''}",
            f"Rollback: {concept.get('rollback_handle') or concept.get('rollback_id') or ''}",
            "",
            "Definition:",
            str(concept.get("short_definition") or "").strip(),
        ]
        for title, key in [
            ("Propositions", "propositions"),
            ("Related Concepts", "related_concepts"),
            ("Examples", "examples"),
            ("Misconceptions", "misconceptions"),
        ]:
            values = concept.get(key)
            if isinstance(values, list) and values:
                lines.extend(["", f"{title}:"])
                lines.extend(f"- {item}" for item in values[:12])
        self._write_database_detail("\n".join(lines))

    def _write_database_detail(self, text: str) -> None:
        self.database_detail.configure(state=tk.NORMAL)
        self.database_detail.delete("1.0", tk.END)
        if text:
            self.database_detail.insert(tk.END, text)
        self.database_detail.configure(state=tk.DISABLED)

    def _append_chat(self, speaker: str, text: str) -> None:
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{speaker}: {text}\n\n")
        self.chat_history.see(tk.END)
        self.chat_history.configure(state=tk.DISABLED)

    def _append_session(self, role: str, content: str) -> None:
        self.session_history.append({"role": role, "content": " ".join(str(content).split())[:1200]})
        if len(self.session_history) > 24:
            self.session_history = self.session_history[-24:]

    def _recent_history_for_router(self) -> list[dict[str, str]]:
        history = self.session_history[-10:]
        if self.active_topic_anchor:
            history = [*history, {"role": "anchor", "content": json.dumps(self.active_topic_anchor, sort_keys=True)}]
        return history

    def _last_substantive_exchange(self) -> dict[str, str] | None:
        last_assistant = ""
        for item in reversed(self.session_history):
            role = item.get("role")
            content = str(item.get("content") or "")
            if role == "assistant" and not last_assistant and "Would you like me to ask the local reasoning model to elaborate?" not in content:
                last_assistant = _assistant_answer_text(content)
            elif role == "user" and last_assistant:
                text = content.strip()
                if text.lower() not in {"yes", "no", "tell me more", "more", "go deeper", "explain more", "elaborate"}:
                    return {"question": text, "answer": last_assistant}
        return None

    def _show_welcome(self) -> None:
        residency = ""
        if self.model_residency_status == "warm":
            residency = " The everyday local model is already loaded for this session."
        elif self.model_residency_status.startswith("warm_failed"):
            residency = " Local model warmup did not complete, so I may need to fall back if you ask for local reasoning."
        self._append_chat(
            "DELTA",
            "Hi. I'm DELTA. You can talk normally here. If a task needs governed memory, evidence review, replay, or diagnostics, I can route it or you can open Advanced mode."
            + residency,
        )
        self._append_session("assistant", "Hi. I'm DELTA. You can talk normally here.")

    def _warm_default_model(self) -> None:
        lane = select_model_lane("Hello DELTA.", "conversation")
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        if not model_id:
            self.model_residency_status = "warm_failed:no_model"
            return
        try:
            self.provider_manager.warm(model_id)
            self.resident_model_id = model_id
            self.resident_lane = str(lane.get("lane") or "everyday_conversation")
            self.model_residency_status = "warm"
        except Exception as exc:  # noqa: BLE001 - UI should stay usable if warmup fails.
            self.model_residency_status = f"warm_failed:{type(exc).__name__}:{str(exc)[:120]}"

    def _prepare_resident_model_for_question(self, question: str) -> None:
        lane = select_model_lane(question)
        model_id = str(lane.get("selected_model_id") or lane.get("selected_model") or "")
        lane_name = str(lane.get("lane") or "")
        display = str(lane.get("display_name") or lane_name or "local model")
        if not model_id:
            return
        if self.resident_model_id == model_id:
            return
        if self.resident_model_id:
            if lane_name == "planning":
                self._append_chat("DELTA", "One moment while I switch to the planning model.")
            elif self.resident_lane == "planning":
                self._append_chat("DELTA", "One moment while I switch back to the general conversation model.")
            else:
                self._append_chat("DELTA", f"One moment while I switch to the {display}.")
        else:
            self._append_chat("DELTA", f"One moment while I load the {display}.")
        try:
            self.provider_manager.warm(model_id)
            self.resident_model_id = model_id
            self.resident_lane = lane_name
            self.model_residency_status = "warm"
        except Exception as exc:  # noqa: BLE001
            self.model_residency_status = f"switch_failed:{type(exc).__name__}:{str(exc)[:120]}"

    def _send_chat(self) -> None:
        message = self.chat_input.get().strip()
        if not message:
            return
        self.chat_input.delete(0, tk.END)
        self._append_chat("You", message)
        lower = message.lower().strip()
        cancel_words = {"no", "n", "not now", "no thanks", "keep chatting", "nevermind", "never mind", "cancel", "stop", "forget it"}
        affirm_words = {"yes", "y", "yes please", "sure", "okay", "ok", "go ahead", "do it", "tell me more", "more", "go deeper"}
        if self.pending_local_model_deepening and lower in affirm_words:
            pending = self.pending_local_model_deepening
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            target = _build_deepening_prompt(pending["question"], pending["answer"])
            self._prepare_resident_model_for_question(target)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            payload.update({
                "active_pending_action_id": pending.get("action_id"),
                "active_pending_action_type": pending.get("action_type", "local_model_deepening"),
                "pending_action_matched": True,
                "action_executed": bool((payload.get("local_model_result") or {}).get("executed")),
                "pending_action_cleared": True,
            })
            enrichment_candidate = build_memory_candidate_from_answer(pending["question"], payload)
            matches = query_approved_concepts(pending["question"]).get("matches", [])
            if matches:
                enrichment_candidate = {
                    **enrichment_candidate,
                    "enrichment_of_concept_id": matches[0].get("concept_id"),
                    "enrichment_of_concept_name": matches[0].get("concept_name"),
                    "approval_status": "pending_operator_enrichment_review",
                    "source_question": pending["question"],
                    "source_type": "local_model_lane_enrichment",
                }
            payload["memory_candidate"] = enrichment_candidate
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_deepening and lower in cancel_words:
            self.pending_local_model_deepening = None
            self._append_session("user", message)
            reply = "Okay. I will not deepen that answer right now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_local_model_question and lower in (affirm_words | {"ask local", "ask the local model", "ask a local model"}):
            target = self.pending_local_model_question
            self.pending_local_model_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
                provider_manager=self.provider_manager,
            )
            self.last_message = target
            self.last_payload = payload
            self._update_active_topic_anchor(payload)
            offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
            self.pending_provider_question = target if isinstance(offer, dict) and offer.get("offered") else None
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_local_model_question and lower in cancel_words:
            self.pending_local_model_question = None
            self._append_session("user", message)
            reply = "Okay. I will leave that unanswered locally for now."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if self.pending_provider_question and lower in {"yes", "y", "yes please", "ask gpt", "ask gpt please", "look for sources"}:
            target = self.pending_provider_question
            self.pending_provider_question = None
            self._append_session("user", message)
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                provider_approved=True,
            )
            self.last_message = target
            self.last_payload = payload
            rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
            self._queue_concept_candidate(payload)
            self._set_deepening_offer_if_present(target, payload)
            self._append_chat("DELTA", rendered)
            self._append_session("assistant", rendered)
            self._refresh_state_cards()
            return
        if self.pending_provider_question and lower in cancel_words:
            self.pending_provider_question = None
            self._append_session("user", message)
            reply = "Okay. I will keep this local and will not ask a provider."
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"remember that", "remember this", "store that", "store this", "save that", "save this", "remember this useful answer", "keep this concept", "that was useful remember the concept"}:
            self._append_session("user", message)
            reply = self._queue_last_answer_for_review()
            self._append_chat("DELTA", reply)
            self._append_session("assistant", reply)
            return
        if lower in {"not now", "discard", "forget after this chat"}:
            self._append_session("user", message)
            self._append_chat("DELTA", "Okay. I will keep this in the current conversation only and will not store a concept.")
            self._append_session("assistant", "Okay. I will keep this in the current conversation only and will not store a concept.")
            return
        self.pending_local_model_deepening = None
        payload = route_message(
            self.mode.get(),
            message,
            self.paste.get("1.0", tk.END) if hasattr(self, "paste") else "",
            history=self._recent_history_for_router(),
            execute_local_model=False,
        )
        self.last_message = message
        self.last_payload = payload
        self._update_active_topic_anchor(payload)
        offer = payload.get("supporting_information_offer") if isinstance(payload, dict) else None
        if isinstance(offer, dict) and offer.get("offered"):
            self.pending_provider_question = message
        elif payload.get("route") == "gpt_support_approval_preview":
            self.pending_provider_question = message
        else:
            self.pending_provider_question = None
        local_offer = payload.get("local_model_offer") if isinstance(payload, dict) else None
        pending_suggestion = payload.get("pending_action_suggestion") if isinstance(payload, dict) else None
        if isinstance(pending_suggestion, dict) and pending_suggestion.get("action_type") == "local_model_deepening":
            exchange = self._last_substantive_exchange() or {"question": message, "answer": str(payload.get("answer") or "")}
            action_id = f"rc2-pending-action-{uuid.uuid4().hex[:12]}"
            self.pending_local_model_deepening = {
                "action_id": action_id,
                "action_type": "local_model_deepening",
                "question": exchange["question"],
                "answer": exchange["answer"],
                "followup_instruction": message,
                "source_turn_id": str(len(self.session_history)),
            }
            payload["pending_action_suggestion"] = {
                **pending_suggestion,
                "action_id": action_id,
                "original_topic": exchange["question"],
                "prior_answer_summary": exchange["answer"][:260],
                "selected_lane": (payload.get("selected_model_lane") or {}).get("lane"),
                "selected_model": (payload.get("selected_model_lane") or {}).get("selected_model_id"),
            }
            self.pending_local_model_question = None
        else:
            self.pending_local_model_question = message if isinstance(local_offer, dict) and local_offer.get("offered") else None
            if self.pending_local_model_question:
                self.pending_local_model_deepening = None
        self._refresh_state_cards()
        rendered = render_route(payload, developer_overlay=self.developer_overlay_enabled.get())
        self._queue_concept_candidate(payload)
        self._append_chat("DELTA", rendered)
        self._append_session("user", message)
        self._append_session("assistant", rendered)

    def _update_active_topic_anchor(self, payload: dict[str, object]) -> None:
        anchor = payload.get("active_topic_anchor")
        if isinstance(anchor, dict) and (anchor.get("active_concept_id") or anchor.get("active_concept_name")):
            self.active_topic_anchor = dict(anchor)
            return
        matches = payload.get("concept_matches")
        if isinstance(matches, list) and matches:
            first = matches[0]
            if isinstance(first, dict) and (first.get("concept_id") or first.get("concept_name")):
                self.active_topic_anchor = {
                    "active_concept_id": first.get("concept_id"),
                    "active_concept_name": first.get("concept_name"),
                    "domain": first.get("domain"),
                    "related_concepts": first.get("related_concepts", [])[:8] if isinstance(first.get("related_concepts"), list) else [],
                    "retrieved_concept_ids": [row.get("concept_id") for row in matches if isinstance(row, dict) and row.get("concept_id")],
                    "retrieved_concept_names": [row.get("concept_name") for row in matches if isinstance(row, dict) and row.get("concept_name")],
                    "last_user_question": self.last_message,
                    "last_answer_summary": " ".join(str(payload.get("answer") or "").split())[:420],
                }

    def _set_deepening_offer_if_present(self, question: str, payload: dict[str, object]) -> None:
        answer = str(payload.get("answer") or "")
        if payload.get("route") == "local_conversation_model_lane" and _model_answer_offers_deepening(answer):
            self.pending_local_model_deepening = {"question": question, "answer": answer}
        else:
            self.pending_local_model_deepening = None

    def _queue_concept_candidate(self, payload: dict[str, object]) -> None:
        candidate = payload.get("memory_candidate")
        if not isinstance(candidate, dict):
            return
        concept_id = str(candidate.get("concept_id") or "")
        if not concept_id or concept_id in self.concept_review_items:
            return
        is_enrichment = bool(candidate.get("enrichment_of_concept_id"))
        concept_label = str(candidate.get("concept_name") or "Learned Concept")
        source_label = str(candidate.get("source_type") or payload.get("route") or "conversation")
        if is_enrichment:
            concept_label = f"Update: {candidate.get('enrichment_of_concept_name') or concept_label}"
            source_label = "enrichment"
        self.concept_review_items[concept_id] = {"candidate": candidate, "payload": payload}
        self.concept_review.insert(
            "",
            tk.END,
            iid=concept_id,
            values=(
                concept_label,
                source_label,
                "pending",
            ),
        )

    def _queue_last_answer_for_review(self) -> str:
        if not self.last_message or not isinstance(self.last_payload, dict):
            return "I do not have a previous answer to turn into a concept yet."
        existing = self.last_payload.get("memory_candidate")
        if isinstance(existing, dict):
            candidate = existing
        else:
            candidate = build_memory_candidate_from_answer(self.last_message, self.last_payload)
            if not candidate_is_memory_worthy(candidate, self.last_payload):
                candidate = {
                    **candidate,
                    "approval_status": "pending_operator_review_user_requested",
                    "operator_review_required": True,
                    "memory_request_source": "explicit_user_remember_that",
                    "uncertainty": "moderate_operator_review_required",
                    "review_note": "User explicitly asked to remember the previous answer; candidate was queued for manual review despite lower automatic memory-worthiness.",
                }
            self.last_payload["memory_candidate"] = candidate
        before = set(self.concept_review_items)
        self._queue_concept_candidate(self.last_payload)
        concept_id = str(candidate.get("concept_id") or "")
        name = str(candidate.get("concept_name") or "that concept")
        if concept_id in before:
            return f"`{name}` is already in Concept Review. Select it and press Accept Selected Concept if you want it stored."
        return f"I added `{name}` to Concept Review. Select it and press Accept Selected Concept if you want it stored."

    def _selected_concept_id(self) -> str | None:
        selected = self.concept_review.selection()
        return str(selected[0]) if selected else None

    def _accept_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = dict(item["candidate"])
        result = approve_candidate_concept(candidate, approval_text="Keep this concept")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        approved = result.get("approved") is True
        duplicate = result.get("duplicate") is True
        if approved:
            concept = result["stored_concept"]
            self.concept_review.set(concept_id, "status", "accepted")
            if result.get("enriched_existing"):
                text = f"Updated the existing concept `{concept['concept_name']}` with the reviewed elaboration. Canonical memory and training stayed off."
            else:
                text = f"Kept the concept `{concept['concept_name']}` in noncanonical {concept['memory_type']} memory. Canonical memory and training stayed off."
        elif duplicate:
            self.concept_review.set(concept_id, "status", "duplicate")
            text = "I already had a matching concept, so I skipped the duplicate. Canonical memory and training stayed off."
        else:
            self.concept_review.set(concept_id, "status", "not stored")
            text = "I did not store the concept. Canonical memory and training stayed off."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _reject_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        self.concept_review.set(concept_id, "status", "rejected")
        item = self.concept_review_items.get(concept_id, {})
        candidate = item.get("candidate", {}) if isinstance(item, dict) else {}
        name = candidate.get("concept_name", "that concept") if isinstance(candidate, dict) else "that concept"
        text = f"Rejected `{name}`. Nothing was stored."
        self._append_chat("DELTA", text)
        self._append_session("assistant", text)

    def _inspect_selected_concept(self) -> None:
        concept_id = self._selected_concept_id()
        if not concept_id:
            messagebox.showinfo("DELTA", "Select a concept from Concept Review first.")
            return
        item = self.concept_review_items.get(concept_id)
        if not item:
            messagebox.showinfo("DELTA", "That concept is no longer available for review.")
            return
        candidate = item["candidate"]
        if not isinstance(candidate, dict):
            messagebox.showinfo("DELTA", "That concept candidate is not editable.")
            return
        self._open_concept_editor(concept_id, candidate)

    def _open_concept_editor(self, concept_id: str, candidate: dict[str, object]) -> None:
        editor = tk.Toplevel(self.root)
        editor.title(f"Edit Concept - {candidate.get('concept_name', 'Candidate')}")
        editor.geometry("780x680")
        editor.transient(self.root)

        frame = ttk.Frame(editor, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)
        frame.rowconfigure(4, weight=1)
        frame.rowconfigure(8, weight=1)

        name_var = tk.StringVar(value=str(candidate.get("concept_name") or ""))
        definition_var = tk.StringVar(value=str(candidate.get("short_definition") or ""))
        uncertainty_var = tk.StringVar(value=str(candidate.get("uncertainty") or ""))
        memory_type_var = tk.StringVar(value=str(candidate.get("memory_type") or "knowledge"))

        ttk.Label(frame, text="Concept name").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Short definition").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=definition_var).grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Propositions").grid(row=2, column=0, sticky="nw", pady=3)
        propositions_box = scrolledtext.ScrolledText(frame, height=7, wrap=tk.WORD)
        propositions_box.grid(row=2, column=1, sticky="nsew", pady=3)
        propositions_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("propositions", []) if str(item).strip()))

        ttk.Label(frame, text="Related concepts").grid(row=3, column=0, sticky="nw", pady=3)
        related_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        related_box.grid(row=3, column=1, sticky="nsew", pady=3)
        related_box.insert(tk.END, "\n".join(str(item) for item in candidate.get("related_concepts", []) if str(item).strip()))

        ttk.Label(frame, text="Operator notes").grid(row=4, column=0, sticky="nw", pady=3)
        notes_box = scrolledtext.ScrolledText(frame, height=5, wrap=tk.WORD)
        notes_box.grid(row=4, column=1, sticky="nsew", pady=3)
        notes_box.insert(tk.END, str(candidate.get("operator_notes") or candidate.get("review_note") or ""))

        ttk.Label(frame, text="Uncertainty").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(frame, textvariable=uncertainty_var).grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Memory type").grid(row=6, column=0, sticky="w", pady=3)
        ttk.Combobox(frame, values=["knowledge", "personal", "conversation"], textvariable=memory_type_var, state="readonly").grid(row=6, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Source question").grid(row=7, column=0, sticky="nw", pady=3)
        source = ttk.Label(frame, text=str(candidate.get("source_question") or ""), wraplength=560)
        source.grid(row=7, column=1, sticky="ew", pady=3)

        ttk.Label(frame, text="Raw candidate").grid(row=8, column=0, sticky="nw", pady=3)
        raw_box = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        raw_box.grid(row=8, column=1, sticky="nsew", pady=3)
        raw_box.insert(tk.END, json.dumps(candidate, indent=2, sort_keys=True))
        raw_box.configure(state=tk.DISABLED)

        def done() -> None:
            updated = {
                **candidate,
                "concept_name": name_var.get().strip() or str(candidate.get("concept_name") or "Learned Concept"),
                "short_definition": definition_var.get().strip(),
                "propositions": _lines_from_text(propositions_box.get("1.0", tk.END)),
                "related_concepts": _lines_from_text(related_box.get("1.0", tk.END)),
                "operator_notes": notes_box.get("1.0", tk.END).strip(),
                "uncertainty": uncertainty_var.get().strip() or "operator_edited",
                "memory_type": memory_type_var.get().strip() or "knowledge",
                "operator_edited": True,
                "approval_status": "pending_operator_review_edited",
            }
            self.concept_review_items[concept_id]["candidate"] = updated
            if self.last_payload and self.last_payload.get("memory_candidate", {}).get("concept_id") == concept_id:
                self.last_payload["memory_candidate"] = updated
            self.concept_review.set(concept_id, "concept", updated["concept_name"])
            self.concept_review.set(concept_id, "source", str(updated.get("source_type") or "edited_candidate"))
            self.concept_review.set(concept_id, "status", "edited")
            self._append_chat("DELTA", f"Updated `{updated['concept_name']}` in Concept Review. It is not stored until you press Accept Selected Concept.")
            self._append_session("assistant", f"Updated `{updated['concept_name']}` in Concept Review.")
            editor.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="Done", command=done).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="Cancel", command=editor.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def _clear_local_store(self) -> None:
        phrase = "DELETE_RC2_DEVELOPMENTAL_MEMORY_STORE"
        entered = simpledialog.askstring(
            "Clear Local Memory Store",
            f"Type {phrase} to delete only the RC2 developmental concept store.",
        )
        result = clear_developmental_memory_store(entered or "")
        self.snapshot = build_operator_snapshot()
        self._refresh_state_cards()
        if result["cleared"]:
            self._append_chat("DELTA", "The RC2 developmental concept store was cleared. Canonical memory, reports, source code, and model weights were untouched.")
        else:
            self._append_chat("DELTA", "Local memory store was not cleared because the confirmation phrase did not match.")

    def _write_output(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

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
        lines.extend(["", "Nothing has been persisted yet.", "Approve extracted propositions to make them available in noncanonical substrate."])
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
            note = "Operator created an empty observation placeholder from the RC2 console."
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
        developmental = build_developmental_memory_state()
        self._refresh_state_cards()
        self._write_output(_format_cognitive_state(state) + "\n\nDevelopmental concept memory\n" + json.dumps(developmental, indent=2, sort_keys=True))

    def _show_review_queue(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["operator_review_queue"], indent=2, sort_keys=True))

    def _show_replay(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["replay_rollback"], indent=2, sort_keys=True))

    def _show_failure_taxonomy(self) -> None:
        self.snapshot = build_operator_snapshot()
        self._write_output(json.dumps(self.snapshot["failure_classification"], indent=2, sort_keys=True))


def main() -> int:
    root = tk.Tk()
    DeltaApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
