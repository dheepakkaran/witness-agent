"""Detector baseline: Llama Prompt Guard 2 (86M, Groq free tier) on every static test document.

The model reads at most 512 tokens, so the raw HTML is split into 1000-character chunks with 150 characters of
overlap; the document score is the maximum chunk score. Threshold 0.5 (PREREG).

    .venv/bin/python scripts/run_pg2.py test
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openai  # noqa: E402

from scripts.run_static import documents  # noqa: E402
from witness.providers import CACHE, ROOT, _groq  # noqa: E402

MODEL = "meta-llama/llama-prompt-guard-2-86m"


def score(text: str) -> float:
    import hashlib
    p = CACHE / f"pg2_{hashlib.sha256(text.encode()).hexdigest()[:32]}.json"
    if p.exists():
        return json.loads(p.read_text())["score"]
    for attempt in range(10):
        try:
            r = _groq().chat.completions.create(model=MODEL, messages=[{"role": "user", "content": text}])
            break
        except openai.RateLimitError:
            time.sleep(5 * (attempt + 1))
    s = float(r.choices[0].message.content.strip())
    p.write_text(json.dumps({"score": s}))
    return s


def doc_score(html: str) -> float:
    chunks = [html[i:i + 1000] for i in range(0, max(1, len(html)), 850)]
    return max(score(c) for c in chunks)


def main(split: str):
    rows = []
    for sc, fam, h in documents(split):
        rows.append({"doc": f"{sc.sid}|{fam}", "sid": sc.sid, "family": fam, "attacked": fam != "clean",
                     "score": doc_score(h)})
    out = ROOT / "results" / f"{split}_pg2.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1])
