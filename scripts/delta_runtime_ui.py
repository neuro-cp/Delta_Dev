from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_local_answer_engine import run_v29_local_answer  # noqa: E402
from orchestration.runtime.v30_conversational_answer_formatter import format_conversational_answer  # noqa: E402
from orchestration.runtime.v30_pipeline_explainer import build_pipeline_explanation  # noqa: E402


def main() -> int:
    root = tk.Tk()
    root.title("DELTA Runtime Console")
    root.geometry("900x620")

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack(fill=tk.BOTH, expand=True)

    entry = tk.Entry(frame)
    entry.pack(fill=tk.X)
    entry.insert(0, "What is DELTA?")

    output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=28)
    output.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def send() -> None:
        message = entry.get().strip()
        if not message:
            return
        if "explain how" in message.lower() or "pipeline" in message.lower():
            data = build_pipeline_explanation(message, use_recall=True)
            rendered = data["rendered_explanation"]
        else:
            data = run_v29_local_answer(message, use_recall=True)
            rendered = format_conversational_answer(data, mode="detailed")
        output.delete("1.0", tk.END)
        output.insert(tk.END, rendered)

    button = tk.Button(frame, text="Send", command=send)
    button.pack(anchor=tk.E, pady=(10, 0))
    entry.bind("<Return>", lambda _event: send())

    send()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
