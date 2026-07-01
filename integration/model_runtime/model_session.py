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

    def generate(self, prompt: str) -> str:
        if self._current_model is None or self._engine is None:
            raise RuntimeError("ModelSession.generate() called with no active model")

        print(f"[ModelSession] Generating with {self._current_model.name}\n")

        full_text = ""

        # -----------------------------
        # JSON grammar (optional)
        # -----------------------------
        grammar = None
        if GRAMMAR_SUPPORTED:
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
