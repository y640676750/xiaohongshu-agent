from pathlib import Path
import random

MEMORY_FILE = "kb/viral_memory.txt"


def load_viral_memory(max_items=10):
    path = Path(MEMORY_FILE)

    if not path.exists():
        return ""

    lines = [
        l.strip()
        for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]

    random.shuffle(lines)

    return "\n".join(lines[:max_items])


def save_viral_pattern(text: str):
    path = Path(MEMORY_FILE)

    if not path.exists():
        path.write_text("", encoding="utf-8")

    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")