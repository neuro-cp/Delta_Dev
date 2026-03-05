import os
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUTPUT_FILE = Path(r"C:\Users\Admin\Desktop\neural_framework_dump.txt")

# File extensions we usually want as "code / text"
TEXT_EXTENSIONS = {
    ".py", ".json", ".txt", ".md", ".yaml", ".yml", ".ini", ".cfg",
    ".csv", ".tsv", ".js", ".html", ".css", ".xml", ".toml"
}

def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS

def read_file_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR READING FILE: {e}]"

def build_file_tree(root: Path) -> str:
    lines = []

    def walk(dir_path: Path, prefix=""):
        entries = sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(entries) - 1 else "│   "
                walk(entry, prefix + extension)

    lines.append(str(root))
    walk(root)
    return "\n".join(lines)

def main():
    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        out.write("=== NEURAL FRAMEWORK FULL CODE DUMP ===\n\n")

        for path in ROOT_DIR.rglob("*"):
            if path.is_file() and is_text_file(path):
                out.write("\n" + "=" * 80 + "\n")
                out.write(f"FILE: {path}\n")
                out.write("=" * 80 + "\n\n")
                out.write(read_file_safely(path))
                out.write("\n")

        out.write("\n\n" + "#" * 80 + "\n")
        out.write("DIRECTORY TREE\n")
        out.write("#" * 80 + "\n\n")
        out.write(build_file_tree(ROOT_DIR))

    print(f"Dump complete → {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
