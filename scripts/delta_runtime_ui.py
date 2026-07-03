from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_first_interaction import build_first_interaction_result, format_first_interaction_cli_output  # noqa: E402


def main() -> int:
    root = tk.Tk()
    root.title("DELTA Runtime Console")
    root.geometry("900x620")

    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack(fill=tk.BOTH, expand=True)

    entry = tk.Entry(frame)
    entry.pack(fill=tk.X)
    entry.insert(0, "What is DELTA's current replay and consolidation path?")

    output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=28)
    output.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def send() -> None:
        message = entry.get().strip()
        if not message:
            return
        data = build_first_interaction_result(message)
        output.delete("1.0", tk.END)
        output.insert(tk.END, format_first_interaction_cli_output(data))

    button = tk.Button(frame, text="Send", command=send)
    button.pack(anchor=tk.E, pady=(10, 0))
    entry.bind("<Return>", lambda _event: send())

    send()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
