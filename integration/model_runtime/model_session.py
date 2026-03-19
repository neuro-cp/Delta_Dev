"""
integration/model_runtime/model_session.py

Model session controller.

Responsibilities
----------------
• Ensure only one model is active at a time
• Manage model lifecycle (load → generate → unload)
• Isolate inference engine interaction from higher layers
• Provide deterministic runtime behavior
"""

from typing import Optional
import os

from llama_cpp import Llama

try:
    # Optional grammar helper (newer llama-cpp builds)
    from llama_cpp import LlamaGrammar
    GRAMMAR_SUPPORTED = True
except Exception:
    GRAMMAR_SUPPORTED = False

from integration.model_runtime.model_registry import ModelSpec


class ModelSession:
    """
    Controls lifecycle of a single active model instance.
    """

    def __init__(self) -> None:
        self._current_model: Optional[ModelSpec] = None
        self._engine: Optional[Llama] = None

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
            verbose=False
        )

        self._current_model = model_spec

    # ------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------

    def generate(self, prompt: str) -> str:

        if self._current_model is None or self._engine is None:
            raise RuntimeError(
                "ModelSession.generate() called with no active model"
            )

        print(f"[ModelSession] Generating with {self._current_model.name}")

        json_grammar = r"""
root ::= object
object ::= "{" ws "\"answer\"" ws ":" ws string ws "," ws "\"confidence\"" ws ":" ws number ws "}"
string ::= "\"" chars "\""
chars ::= char*
char ::= [^"\\] | escape
escape ::= "\\" ["\\/bfnrt]
number ::= "-"? digit+ ("." digit+)?
digit ::= [0-9]
ws ::= [ \t\n\r]*
"""

        # --------------------------------------------------------
        # Use grammar if supported
        # --------------------------------------------------------

        if GRAMMAR_SUPPORTED:
            grammar = LlamaGrammar.from_string(json_grammar)

            result = self._engine(
                prompt,
                max_tokens=1000,
                temperature=0.4,
                grammar=grammar
            )
        else:
            # fallback if grammar support missing
            result = self._engine(
                prompt,
                max_tokens=1000,
                temperature=0.4
            )

        text = result["choices"][0]["text"]

        return text.strip()

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