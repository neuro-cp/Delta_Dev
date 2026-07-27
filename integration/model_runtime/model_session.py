"""
integration/model_runtime/model_session.py

Model session controller.

Responsibilities
----------------
• Ensure only one model is active at a time
• Manage model lifecycle (load → generate → unload)
• Provide streaming token output
• Preserve deterministic runtime behavior
• Support optional structured JSON grammar
"""

from typing import Optional
import os

from llama_cpp import Llama

try:
    from llama_cpp import LlamaGrammar
    GRAMMAR_SUPPORTED = True
except Exception:
    GRAMMAR_SUPPORTED = False

from integration.model_runtime.model_registry import ModelSpec


COGNITIVE_OPERATION_FIELDS = {
    "interpret_state": ("state_summary", "salient_observations", "evidence_refs", "unresolved_questions", "uncertainty", "recommended_next_operation"),
    "prioritize_focus": ("selected_focus_id", "selection_reason", "supporting_evidence_refs", "rejected_focus_ids", "uncertainty", "recommended_state_transition"),
    "formulate_hypothesis": ("hypothesis_statement", "scope", "supporting_evidence_refs", "assumptions", "expected_observations", "uncertainty", "recommended_state_transition"),
    "identify_evidence_need": ("target_claim_or_decision", "known_evidence_refs", "missing_fact", "why_missing_fact_matters", "acceptable_evidence_source", "bounded_retrieval_action", "stop_condition", "uncertainty", "recommended_state_transition"),
    "challenge_hypothesis": ("challenged_hypothesis_id", "vulnerability", "contrary_evidence_refs", "disconfirming_observation", "uncertainty", "recommended_state_transition"),
    "revise_hypothesis": ("prior_hypothesis_id", "revised_statement", "evidence_refs", "contrary_evidence_considered", "revision_reason", "new_confidence_state", "uncertainty", "recommended_state_transition"),
    "propose_plan": ("plan_summary", "supporting_evidence_refs", "planned_steps", "risks", "uncertainty", "recommended_state_transition"),
    "revise_plan": ("prior_plan_id", "revised_plan_summary", "evidence_refs", "revision_reason", "uncertainty", "recommended_state_transition"),
    "reflect_on_outcome": ("expected_outcome", "observed_outcome", "discrepancy", "evidence_refs", "lesson", "uncertainty", "recommended_state_transition"),
    "summarize_learning": ("lesson", "evidence_refs", "unresolved_questions", "uncertainty", "recommended_state_transition"),
    "select_next_focus": ("selected_focus_id", "salience_reason", "related_goal_ids", "evidence_refs", "deferred_focus_ids", "uncertainty", "recommended_state_transition"),
    "request_operator_resolution": ("question", "blocking_reason", "evidence_refs", "options", "uncertainty", "recommended_state_transition"),
    "declare_blocked_capability": ("capability_gap", "attempted_evidence_refs", "blocking_reason", "bounded_next_action", "uncertainty", "recommended_state_transition"),
    "declare_insufficient_evidence": ("missing_evidence", "attempted_evidence_refs", "why_existing_evidence_is_insufficient", "bounded_next_evidence_request", "uncertainty", "recommended_state_transition"),
}
COGNITIVE_ARRAY_FIELDS = {
    "assumptions",
    "attempted_evidence_refs",
    "contrary_evidence_considered",
    "contrary_evidence_refs",
    "deferred_focus_ids",
    "evidence_refs",
    "existing_evidence_refs",
    "expected_observations",
    "missing_evidence",
    "known_evidence_refs",
    "options",
    "planned_steps",
    "related_goal_ids",
    "rejected_focus_ids",
    "risks",
    "salient_observations",
    "supporting_evidence_refs",
    "unresolved_questions",
}
COGNITIVE_OPERATION_ENUM_FIELDS = {
    "interpret_state": {
        "recommended_next_operation": (
            "prioritize_focus",
            "formulate_hypothesis",
            "identify_evidence_need",
            "compare_evidence",
            "declare_insufficient_evidence",
        ),
    },
    "prioritize_focus": {
        "recommended_state_transition": ("select_next_focus", "continue_focus", "request_operator_resolution"),
    },
    "formulate_hypothesis": {
        "recommended_state_transition": ("propose_hypothesis", "declare_insufficient_evidence"),
    },
    "identify_evidence_need": {
        "recommended_state_transition": ("request_evidence",),
    },
    "compare_evidence": {
        "operation_result_type": ("compare_evidence_result",),
        "recommended_state_transition": ("add_supporting_evidence", "add_conflicting_evidence", "weaken_hypothesis", "revise_hypothesis"),
    },
    "challenge_hypothesis": {
        "recommended_state_transition": ("weaken_hypothesis", "revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
    },
    "revise_hypothesis": {
        "recommended_state_transition": ("revise_hypothesis", "reject_hypothesis", "falsify_hypothesis"),
    },
    "propose_plan": {
        "recommended_state_transition": ("propose_plan", "request_operator_resolution", "declare_insufficient_evidence"),
    },
    "revise_plan": {
        "recommended_state_transition": ("revise_plan", "request_operator_resolution", "declare_insufficient_evidence"),
    },
    "reflect_on_outcome": {
        "recommended_state_transition": ("reflect_on_outcome", "weaken_hypothesis", "revise_hypothesis", "summarize_learning"),
    },
    "summarize_learning": {
        "recommended_state_transition": ("summarize_learning", "select_next_focus"),
    },
    "select_next_focus": {
        "recommended_state_transition": ("select_next_focus", "request_operator_resolution"),
    },
    "request_operator_resolution": {
        "recommended_state_transition": ("request_operator_resolution",),
    },
    "declare_blocked_capability": {
        "recommended_state_transition": ("declare_blocked_capability",),
    },
    "declare_insufficient_evidence": {
        "recommended_state_transition": ("declare_insufficient_evidence",),
    },
}


def cognitive_operation_grammar(operation_type: str = "") -> str:
    fields = COGNITIVE_OPERATION_FIELDS.get(operation_type) or (
        "assumptions",
        "contrary_evidence_considered",
        "evidence_refs",
        "interpretation",
        "next_evidence_need",
        "next_focus_proposal",
        "operation_result_type",
        "recommended_action",
        "recommended_state_transition",
        "uncertainty",
    )
    enum_fields = COGNITIVE_OPERATION_ENUM_FIELDS.get(operation_type, {})
    parts = []
    enum_rules = []
    for field in fields:
        if field in enum_fields:
            rule = "enum-" + field.replace("_", "-")
            values = enum_fields[field]
            alternatives = " | ".join('"\\"' + value + '\\""' for value in values)
            enum_rules.append(rule + " ::= " + alternatives)
        else:
            rule = "stringlist" if field in COGNITIVE_ARRAY_FIELDS else "string"
        parts.append('"\\"' + field + '\\"" ws ":" ws ' + rule)
    object_rule = ' ws "," ws '.join(parts)
    return (
        'root ::= object\n'
        + 'object ::= "{" ws ' + object_rule + ' ws "}"\n'
        + ("\n".join(enum_rules) + "\n" if enum_rules else "")
        + 'stringlist ::= "[" ws stringitems? ws "]"\n'
        'stringitems ::= string (ws "," ws string)*\n'
        'string ::= "\\\"" chars "\\""\n'
        'chars ::= char+\n'
        'char ::= [^"\\\\] | escape\n'
        'escape ::= "\\\\" ["\\\\/bfnrt]\n'
        'ws ::= [ \\t\\n\\r]*\n'
    )


class ModelSession:
    """
    Controls lifecycle of a single active model instance.
    """

    def __init__(self, *, n_gpu_layers: int | None = None) -> None:
        self._current_model: Optional[ModelSpec] = None
        self._engine: Optional[Llama] = None
        self._n_gpu_layers = self._resolve_gpu_layers(n_gpu_layers)

    # ------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------

    def load(self, model_spec: ModelSpec) -> None:
        if self._current_model is not None:
            if self._current_model.name == model_spec.name:
                return
            self.unload()

        print(f"[ModelSession] Loading model: {model_spec.name}")
        print(f"[ModelSession] Path: {model_spec.path}")

        cpu_threads = max(2, os.cpu_count() // 2)

        self._engine = Llama(
            model_path=model_spec.path,
            n_ctx=model_spec.context_length,
            n_threads=cpu_threads,
            n_gpu_layers=self._n_gpu_layers,
            verbose=False,
        )

        self._current_model = model_spec

    # ------------------------------------------------------------
    # Inference (STREAMING)
    # ------------------------------------------------------------

    def generate(self, prompt: str, *, structured_json: bool = True, cognitive_json: bool = False, cognitive_operation_type: str = "") -> str:
        if self._current_model is None or self._engine is None:
            raise RuntimeError("ModelSession.generate() called with no active model")

        print(f"[ModelSession] Generating with {self._current_model.name}\n")

        full_text = ""

        # -----------------------------
        # JSON grammar (optional)
        # -----------------------------
        grammar = None
        if cognitive_json and GRAMMAR_SUPPORTED:
            try:
                grammar = LlamaGrammar.from_string(cognitive_operation_grammar(cognitive_operation_type))
            except Exception:
                grammar = None
        elif structured_json and GRAMMAR_SUPPORTED:
            try:
                grammar = LlamaGrammar.from_string(r"""
root ::= object
object ::= "{" ws "\"answer\"" ws ":" ws string ws "," ws "\"confidence\"" ws ":" ws number ws "}"
string ::= "\"" chars "\""
chars ::= char*
char ::= [^"\\] | escape
escape ::= "\\" ["\\/bfnrt]
number ::= "-"? digit+ ("." digit+)?
digit ::= [0-9]
ws ::= [ \t\n\r]*
""")
            except Exception:
                grammar = None

        # -----------------------------
        # Streaming call
        # -----------------------------
        try:
            max_tokens = self._resolve_max_tokens()
            stream = self._engine(
                prompt,
                max_tokens=max_tokens,
                temperature=0.4,
                stream=True,
                stop=["}\n\n", "}\r\n\r\n"],
                grammar=grammar if grammar else None,
            )
        except TypeError:
            # Some llama-cpp builds don't allow grammar + stream together
            stream = self._engine(
                prompt,
                max_tokens=self._resolve_max_tokens(),
                temperature=0.4,
                stream=True,
            )

        # -----------------------------
        # Stream tokens live (with passive confidence tracking)
        # -----------------------------
        running_conf = 0.0
        token_count = 0

        for chunk in stream:
            token = chunk["choices"][0]["text"]

            if not token:
                continue

            # Print live (streaming)
            print(token, end="", flush=True)

            full_text += token
            token_count += 1

            # --- lightweight confidence signal (non-intrusive) ---
            if len(full_text) > 50:
                running_conf += 0.01

            if "confidence" in full_text:
                running_conf += 0.03

            running_conf = min(1.0, running_conf)

        print("\n")  # clean newline after completion

        # Optional debug (remove later)
        # print(f"[STREAM CONF] {running_conf:.3f}")

        return full_text.strip()

    # ------------------------------------------------------------
    # Unload
    # ------------------------------------------------------------

    def unload(self) -> None:
        if self._current_model is None:
            return

        print(f"[ModelSession] Unloading model: {self._current_model.name}")

        self._engine = None
        self._current_model = None

    # ------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------

    def active_model(self) -> Optional[str]:
        if self._current_model is None:
            return None
        return self._current_model.name

    def _resolve_gpu_layers(self, configured: int | None) -> int:
        if configured is not None:
            return int(configured)
        raw = os.getenv("DELTA_N_GPU_LAYERS", "").strip()
        if not raw:
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0

    def _resolve_max_tokens(self) -> int:
        raw = os.getenv("DELTA_MAX_TOKENS", "").strip()
        if not raw:
            return 1000
        try:
            return max(1, int(raw))
        except ValueError:
            return 1000
