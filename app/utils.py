from datetime import datetime
from pathlib import Path

def save_output(text: str, prefix: str = "post") -> str:
    Path("outputs").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path("outputs") / f"{prefix}_{ts}.md"
    path.write_text(text, encoding="utf-8")
    return str(path)