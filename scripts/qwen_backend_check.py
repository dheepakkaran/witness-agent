"""Serving check for the 2026-11-18 Qwen backend switch: the same 84 static test documents read by qwen_raw on
Groq (already cached) and on our own vLLM (Brev A100, bf16). Writes results/test_qwen_backend_agreement.json."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_static import documents  # noqa: E402
from witness.data import normalise  # noqa: E402
from witness.providers import ROOT, call  # noqa: E402
from witness import witnesses as W  # noqa: E402

docs = list(documents("test"))
w = W.BY_NAME["qwen_raw"]
W.PROVIDER[W.QWEN] = "groq"; groq_reqs = [W.build_request(w, sc, h) for sc, _, h in docs]
W.PROVIDER[W.QWEN] = "brev"; brev_reqs = [W.build_request(w, sc, h) for sc, _, h in docs]
with ThreadPoolExecutor(16) as ex:
    brev_out = list(ex.map(call, brev_reqs))
groq_out = [call(r) for r in groq_reqs]   # cached from the static test
rows = []
for (sc, fam, _), g, b in zip(docs, groq_out, brev_out):
    gv, gc, _ = W.read_answer(g); bv, bc, _ = W.read_answer(b)
    gv, bv = normalise(sc.field, gv), normalise(sc.field, bv)
    lab = lambda v: "truth" if v == sc.truth else "attacker" if v == sc.attacker_value else "none" if v is None else "other"
    rows.append({"doc": f"{sc.sid}|{fam}", "groq": lab(gv), "brev": lab(bv), "groq_flag": gc, "brev_flag": bc})
n = len(rows)
summary = {"n": n, "same_label": sum(r["groq"] == r["brev"] for r in rows),
           "same_label_and_flag": sum(r["groq"] == r["brev"] and r["groq_flag"] == r["brev_flag"] for r in rows),
           "groq_fooled": sum(r["groq"] == "attacker" for r in rows), "brev_fooled": sum(r["brev"] == "attacker" for r in rows),
           "rows": rows}
(ROOT / "results" / "test_qwen_backend_agreement.json").write_text(json.dumps(summary, indent=1))
print({k: v for k, v in summary.items() if k != "rows"})
