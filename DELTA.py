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
)


def _format_cognitive_state(state: dict[str, object]) -> str:
    return "\n".join([
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
    ])


def _format_snapshot(snapshot: dict[str, object]) -> str:
    status = snapshot["runtime_status"]
    corpus = snapshot["corpus_substrate"]
    replay = snapshot["replay_rollback"]
    queue = snapshot["operator_review_queue"]
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
        self.root.geometry("1180x780")
        self.snapshot = build_operator_snapshot()
        self.extracted: list[dict[str, object]] = []
        self.last_message = ""
        self.last_payload: dict[str, object] | None = None
        self.concept_review_items: dict[str, dict[str, object]] = {}
        self.session_history: list[dict[str, str]] = []
        self.pending_provider_question: str | None = None
        self.pending_local_model_question: str | None = None
        self.pending_local_model_deepening: dict[str, str] | None = None
        self.developer_overlay_enabled = tk.BooleanVar(value=True)
        if not validate_console_safe(self.snapshot):
            raise RuntimeError("DELTA console safety validation failed")
        self._build()
        self._refresh_state_cards()
        self._show_welcome()

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.conversation_tab = ttk.Frame(self.notebook, padding=10)
        self.advanced_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.conversation_tab, text="Conversation")
        self.notebook.add(self.advanced_tab, text="Advanced / Operator Console")

        self._build_conversation_tab()
        self._build_advanced_tab()

    def _build_conversation_tab(self) -> None:
        header = ttk.LabelFrame(self.conversation_tab, text="Cognitive State")
        header.pack(fill=tk.X)
        self.state_vars: dict[str, tk.StringVar] = {}
        for index, (label, key) in enumerate([
            ("Knowledge", "knowledge_available"),
            ("Propositions", "noncanonical_propositions"),
            ("Evidence", "evidence_links"),
            ("Concepts", "concepts"),
            ("Contradictions", "contradictions"),
            ("Replay", "replay_queue"),
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

    def _refresh_state_cards(self) -> None:
        state = build_cognitive_state()
        developmental = build_developmental_memory_state()
        state = {
            **state,
            "knowledge_available": state["knowledge_available"] or developmental["knowledge_memory_records"] > 0,
            "concepts": state["concepts"] + developmental["knowledge_memory_records"],
            "contradictions": state["contradictions"] + developmental["concept_contradictions"],
            "replay_queue": state["replay_queue"] + developmental["concept_replay_queue"],
        }
        for key, var in self.state_vars.items():
            var.set(str(state[key]))

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
        return self.session_history[-10:]

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
        self._append_chat(
            "DELTA",
            "Hi. I'm DELTA. You can talk normally here. If a task needs governed memory, evidence review, replay, or diagnostics, I can route it or you can open Advanced mode.",
        )
        self._append_session("assistant", "Hi. I'm DELTA. You can talk normally here.")

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
            payload = route_message(
                "Conversation",
                target,
                history=self._recent_history_for_router(),
                execute_local_model=True,
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
            )
            self.last_message = target
            self.last_payload = payload
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
