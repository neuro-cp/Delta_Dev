# dump.py
# Dump the entire contents of the ./regions folder into a single .txt file.
#
# Usage (from repo root):
#   python dump.py
#
# Optional:
#   python dump.py --out REGIONS_DUMP.txt
#   python dump.py --max-bytes 0          # 0 = no per-file cap (can get huge)
#   python dump.py --max-bytes 2000000    # 2MB cap per file
#   python dump.py --root "C:\path\to\repo"
#   python dump.py --regions "C:\path\to\repo\regions"

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _looks_binary(data: bytes) -> bool:
    # Heuristic: any NUL byte => almost certainly binary
    if b"\x00" in data:
        return True
    # If a lot of bytes are non-text-ish, treat as binary
    # (very conservative: only flags when quite extreme)
    if not data:
        return False
    bad = 0
    sample = data[:4096]
    for b in sample:
        if b < 9:  # control chars below tab
            bad += 1
    return (bad / max(1, len(sample))) > 0.05


def _safe_decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _cap_content(text: str, max_bytes: int) -> Tuple[str, Optional[str]]:
    """
    Returns (content, note). If capped, note explains head/tail slicing.
    """
    if max_bytes <= 0:
        return text, None

    b = text.encode("utf-8", errors="replace")
    if len(b) <= max_bytes:
        return text, None

    # Keep head+tail, split roughly evenly
    half = max_bytes // 2
    head = b[:half]
    tail = b[-half:] if half > 0 else b""

    out = (
        head.decode("utf-8", errors="replace")
        + "\n\n[... CONTENT TRUNCATED ...]\n\n"
        + tail.decode("utf-8", errors="replace")
    )
    note = f"TRUNCATED: original_bytes={len(b)} max_bytes={max_bytes} (head+tail)"
    return out, note


def _pretty_json(text: str) -> Optional[str]:
    try:
        obj = json.loads(text)
    except Exception:
        return None
    try:
        return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default="", help="Repo root (defaults to directory containing dump.py)")
    ap.add_argument("--regions", type=str, default="", help="Path to regions folder (defaults to <root>/regions)")
    ap.add_argument("--out", type=str, default="REGIONS_DUMP.txt", help="Output .txt filename or path")
    ap.add_argument(
        "--max-bytes",
        type=int,
        default=1_000_000,
        help="Per-file cap in bytes for embedded content. 0 disables capping.",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent
    regions_dir = Path(args.regions).resolve() if args.regions else (root / "regions")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()

    if not regions_dir.exists() or not regions_dir.is_dir():
        raise SystemExit(f"[ERROR] regions folder not found: {regions_dir}")

    files = sorted(
        [p for p in regions_dir.rglob("*") if p.is_file()],
        key=lambda p: str(p).lower(),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("=== REGIONS DUMP ===\n")
        f.write(f"Generated: {now}\n")
        f.write(f"Root: {root}\n")
        f.write(f"Regions: {regions_dir}\n")
        f.write(f"File count: {len(files)}\n")
        f.write(f"Per-file cap (bytes): {args.max_bytes}\n")
        f.write("\n")

        # Index
        f.write("=== FILE INDEX ===\n")
        for p in files:
            rel = p.relative_to(regions_dir)
            try:
                size = p.stat().st_size
            except Exception:
                size = -1
            f.write(f"- {rel}  ({size} bytes)\n")
        f.write("\n")

        # Full content
        f.write("=== FILE CONTENTS ===\n\n")
        for p in files:
            rel = p.relative_to(regions_dir)
            try:
                st = p.stat()
                size = st.st_size
                mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                size = -1
                mtime = "unknown"

            f.write("#" * 90 + "\n")
            f.write(f"FILE: {rel}\n")
            f.write(f"ABS:  {p}\n")
            f.write(f"SIZE: {size} bytes\n")
            f.write(f"MTIME:{mtime}\n")
            f.write("#" * 90 + "\n\n")

            data = _read_bytes(p)

            if _looks_binary(data):
                f.write("[BINARY DETECTED] Skipping raw content.\n\n")
                continue

            raw_text = _safe_decode(data)

            # If JSON, pretty-print for readability (but still "info inside")
            pretty = _pretty_json(raw_text) if p.suffix.lower() == ".json" else None
            content = pretty if pretty is not None else raw_text

            content, note = _cap_content(content, args.max_bytes)
            if note:
                f.write(f"[{note}]\n\n")

            f.write(content.rstrip() + "\n\n")

    print("[OK] Regions dump written to:")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
