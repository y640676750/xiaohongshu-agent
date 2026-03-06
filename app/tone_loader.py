from pathlib import Path


def load_tone_samples(max_samples=5) -> str:
    path = Path("kb/tone_pool/samples")

    if not path.exists():
        return "暂无语感样本"

    files = sorted(path.glob("*.md"))[-max_samples:]

    texts = []
    for f in files:
        texts.append(f.read_text(encoding="utf-8")[:1500])

    return "\n\n".join(texts) if texts else "暂无语感样本"