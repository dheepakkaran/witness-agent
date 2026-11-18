"""Static run: every scenario x (clean + 6 static attacks) x 9 witnesses.

    .venv/bin/python scripts/run_static.py dev      # pipeline check, may be rerun
    .venv/bin/python scripts/run_static.py test     # run ONCE, after the PREREG commit

Writes results/<split>_static.jsonl (one row per document x witness).
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from witness.data import INVISIBLE, inject, make_split, normalise, static_attacks  # noqa: E402
from witness.providers import ROOT, call, claude_batch, openai_batch, spent  # noqa: E402
from witness.render import Renderer  # noqa: E402
from witness.witnesses import WITNESSES, build_request, read_answer, translate, translation_request  # noqa: E402


def scenarios(split: str):
    """dev: all 12. test: 12 of 36 (2 per field: positions 0 and 2 within each field) - see PREREG."""
    scs = make_split(split)
    return scs if split == "dev" else [s for i, s in enumerate(scs) if (i % 6) in (0, 2)]


def documents(split: str):
    for sc in scenarios(split):
        yield sc, "clean", sc.html
        for fam, snip in static_attacks(sc).items():
            yield sc, fam, inject(sc.html, snip)


def main(split: str, only: set[str] | None = None):
    docs = list(documents(split))
    print(f"{split}: {len(docs)} documents x {len(WITNESSES)} witnesses", flush=True)

    with Renderer() as r:
        pngs = [r.png(h) for _, _, h in docs]
    print("rendered", flush=True)

    claude_batch([translation_request(h) for _, _, h in docs])
    tamil = [translate(h) for _, _, h in docs]  # cached by the batch; any dropped item is retried here
    print(f"translated (anthropic spent ${spent('anthropic'):.2f})", flush=True)

    ws = [w for w in WITNESSES if not only or w.name in only]
    reqs = [(i, w, build_request(w, sc, h, png=pngs[i], tamil=tamil[i]))
            for i, (sc, fam, h) in enumerate(docs) for w in ws]

    def run_pool(items, n):
        with ThreadPoolExecutor(n) as ex:
            list(ex.map(lambda t: call(t[2]), items))

    t_oa = threading.Thread(target=openai_batch, args=([x[2] for x in reqs if x[2].provider == "openai"],))
    t_gq = threading.Thread(target=run_pool, args=([x for x in reqs if x[2].provider == "groq"], 1))
    t_oa.start(); t_gq.start()
    claude_batch([x[2] for x in reqs if x[2].provider == "anthropic"])
    t_oa.join(); t_gq.join()

    rows = []
    for i, w, req in reqs:
        sc, fam, _ = docs[i]
        out = call(req)  # all cached by now (retries anything a batch dropped)
        usd = out.get("usd", 0.0)
        raw, conflict, status = read_answer(out)
        v = normalise(sc.field, raw)
        rows.append({
            "doc": f"{sc.sid}|{fam}", "sid": sc.sid, "field": sc.field, "family": fam,
            "attacked": fam != "clean", "invisible": fam in INVISIBLE, "witness": w.name,
            "model": w.model, "view": w.view, "value": v, "raw": raw, "conflict": conflict, "status": status,
            "truth": sc.truth, "attacker": sc.attacker_value,
            "correct": v == sc.truth, "fooled": v == sc.attacker_value, "usd": usd,
        })
    out_path = ROOT / "results" / f"{split}_static.jsonl"
    out_path.write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    print(f"wrote {out_path} ({len(rows)} rows); spent anthropic ${spent('anthropic'):.2f} openai ${spent('openai'):.2f}")


if __name__ == "__main__":
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    main(sys.argv[1], only)
