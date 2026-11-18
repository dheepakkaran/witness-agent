"""Model calls for Claude (Anthropic SDK), GPT (OpenAI SDK) and open models on Groq.

Every call goes through `call()` / `claude_batch()`:
  * a disk cache keyed by the full request, so a rerun never pays twice and
    results are reproducible from `results/cache/`;
  * an SQLite cost ledger (`results/ledger.sqlite`) with a hard cap per provider.

Claude refusals are recorded as they are (stop_reason "refusal"). Server-side
fallbacks are deliberately NOT enabled: a fallback would silently swap the
witness's model and contaminate the measurement.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "results" / "cache"
LEDGER = ROOT / "results" / "ledger.sqlite"

# $ per 1M tokens (input, output). Claude from the claude-api skill (2026-11-03),
# GPT-5.5 from OpenAI's published price ($5 / $30). Batch = 50%.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "gpt-5.5": (5.0, 30.0),
    "gpt-5.4-nano": (0.20, 1.25),
}
CAPS = {"anthropic": float(os.environ.get("CAP_ANTHROPIC", 11)), "openai": float(os.environ.get("CAP_OPENAI", 18)),
        "groq": 0.0, "brev": 0.0}


def _load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if v and k not in os.environ:
                    os.environ[k] = v


_load_env()


class BudgetExceeded(RuntimeError):
    pass


_lock = threading.Lock()


def _db():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(LEDGER)
    con.execute("create table if not exists calls (ts real, provider text, model text, tag text, "
                "in_tok int, out_tok int, usd real, batch int, key text)")
    return con


def spent(provider: str | None = None) -> float:
    with _lock, _db() as con:
        if provider:
            return con.execute("select coalesce(sum(usd),0) from calls where provider=?", (provider,)).fetchone()[0]
        return con.execute("select coalesce(sum(usd),0) from calls").fetchone()[0]


def _record(provider, model, tag, it, ot, batch, key):
    pin, pout = PRICES.get(model, (0.0, 0.0))
    usd = (it * pin + ot * pout) / 1e6 * (0.5 if batch else 1.0)
    with _lock, _db() as con:
        con.execute("insert into calls values (?,?,?,?,?,?,?,?,?)", (time.time(), provider, model, tag, it, ot, usd, int(batch), key))
    return usd


def _check_cap(provider, upcoming: float = 0.0):
    cap = CAPS[provider]
    if cap and spent(provider) + upcoming >= cap:
        raise BudgetExceeded(f"{provider} cap ${cap}: spent ${spent(provider):.2f} + next ${upcoming:.2f} would pass it")


def estimate(reqs, batch=False, out_tokens=350) -> float:
    """Rough upper estimate of what a list of requests will cost (chars/3 tokens, +1100 per image)."""
    usd = 0.0
    for r in reqs:
        pin, pout = PRICES.get(r.model, (0.0, 0.0))
        tin = (len(r.system) + len(r.text)) / 3 + (1100 if r.image else 0)
        tout = min(r.max_tokens, out_tokens if r.schema else 2500)
        usd += (tin * pin + tout * pout) / 1e6
    return usd * (0.5 if batch else 1.0)


@dataclass
class Request:
    provider: str            # anthropic | openai | groq
    model: str
    system: str
    text: str                # user text
    image: Path | None = None
    schema: dict | None = None
    effort: str = "low"
    max_tokens: int = 4000
    tag: str = ""

    def key(self) -> str:
        img = hashlib.sha256(self.image.read_bytes()).hexdigest() if self.image else ""
        blob = json.dumps([self.provider, self.model, self.system, self.text, img, self.schema, self.effort, self.max_tokens],
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:32]


def cached(req: Request) -> dict | None:
    p = CACHE / f"{req.key()}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _store(req: Request, out: dict):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = dict(out, key=req.key(), provider=req.provider, model=req.model, tag=req.tag)
    (CACHE / f"{req.key()}.json").write_text(json.dumps(out, ensure_ascii=False))
    return out


def _b64(p: Path) -> str:
    return base64.standard_b64encode(p.read_bytes()).decode()


# ---------------------------------------------------------------- clients

_clients = {}


def _anthropic():
    import anthropic
    if "a" not in _clients:
        _clients["a"] = anthropic.Anthropic(max_retries=6)
    return _clients["a"]


def _openai():
    import openai
    if "o" not in _clients:
        _clients["o"] = openai.OpenAI(max_retries=6)
    return _clients["o"]


def _groq():
    import openai
    if "g" not in _clients:
        _clients["g"] = openai.OpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.environ["GROQ_API_KEY"], max_retries=8)
    return _clients["g"]


def _anthropic_params(req: Request) -> dict:
    content = []
    if req.image:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": _b64(req.image)}})
    content.append({"type": "text", "text": req.text})
    params = {"model": req.model, "max_tokens": req.max_tokens, "system": req.system,
              "messages": [{"role": "user", "content": content}], "output_config": {"effort": req.effort}}
    if req.schema:
        params["output_config"]["format"] = {"type": "json_schema", "schema": req.schema}
    return params


def _parse_anthropic(msg) -> dict:
    text = "".join(b.text for b in msg.content if b.type == "text")
    return {"text": text, "stop": msg.stop_reason, "in": msg.usage.input_tokens, "out": msg.usage.output_tokens}


def _call_anthropic(req: Request) -> dict:
    r = _anthropic().messages.create(**_anthropic_params(req))
    return _parse_anthropic(r)


def _call_openai(req: Request) -> dict:
    r = _openai().responses.create(**_openai_body(req))
    return {"text": r.output_text, "stop": r.status, "in": r.usage.input_tokens, "out": r.usage.output_tokens}


_groq_lock = threading.Lock()
GROQ_FILE_LOCK = ROOT / "results" / "groq.lock"


def _call_groq(req: Request) -> dict:
    """Free tier: 8,000 tokens/min. A file lock serialises Groq calls across all running processes, and rate-limit
    errors wait for Groq's own retry-after time, for up to 30 minutes in total."""
    import fcntl
    import openai
    sys = req.system
    if req.schema:
        sys += "\nReply with one JSON object only, matching this JSON schema: " + json.dumps(req.schema)
    extra = {"reasoning_format": "hidden"} if "qwen" in req.model else {}
    waited = 0.0
    with _groq_lock, open(GROQ_FILE_LOCK, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        while True:
            try:
                r = _groq().with_options(max_retries=0, timeout=45).chat.completions.create(
                    model=req.model, max_tokens=min(req.max_tokens, 900),
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": req.text}],
                    response_format={"type": "json_object"} if req.schema else None, extra_body=extra)
                break
            except openai.RateLimitError as e:
                ra = e.response.headers.get("retry-after")
                pause = min(120.0, float(ra) + 1 if ra else 20.0)
                waited += pause
                if waited > 1800:
                    raise RuntimeError("groq rate limit: waited 30 min") from e
                time.sleep(pause)
            except (openai.APIConnectionError, openai.InternalServerError):
                waited += 10
                if waited > 1800:
                    raise
                time.sleep(10)
            except openai.BadRequestError as e:  # e.g. json validation failure on the model side
                return {"text": "", "stop": f"error:{str(e)[:200]}", "in": 0, "out": 0}
    return {"text": r.choices[0].message.content or "", "stop": r.choices[0].finish_reason,
            "in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}


VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:18000/v1")
VLLM_MODEL = {"qwen/qwen3.8-27b": "Qwen/Qwen3.8-27B"}  # same open weights Groq serves, bf16 on an A100 80GB (Brev)


def _vllm():
    import openai
    if "v" not in _clients:
        _clients["v"] = openai.OpenAI(base_url=VLLM_URL, api_key="local", max_retries=6, timeout=300)
    return _clients["v"]


def _call_vllm(req: Request) -> dict:
    """Same request shape as _call_groq (system + JSON-schema hint, JSON mode, max 900 tokens, reasoning hidden:
    vLLM's qwen3 reasoning parser keeps the thinking out of `content`)."""
    sys = req.system
    if req.schema:
        sys += "\nReply with one JSON object only, matching this JSON schema: " + json.dumps(req.schema)
    import openai
    for attempt in range(19):  # the SSH tunnel can drop; tunnel.sh reconnects within seconds
        try:
            r = _vllm().chat.completions.create(
                model=VLLM_MODEL[req.model], max_tokens=min(req.max_tokens, 900),
                messages=[{"role": "system", "content": sys}, {"role": "user", "content": req.text}],
                response_format={"type": "json_object"} if req.schema else None)
            break
        except (openai.APIConnectionError, openai.InternalServerError):
            if attempt == 18:
                raise
            time.sleep(10)
    return {"text": r.choices[0].message.content or "", "stop": r.choices[0].finish_reason,
            "in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}


def call(req: Request) -> dict:
    hit = cached(req)
    if hit:
        return hit
    _check_cap(req.provider, estimate([req]))
    fn = {"anthropic": _call_anthropic, "openai": _call_openai, "groq": _call_groq, "brev": _call_vllm}[req.provider]
    out = fn(req)
    out["usd"] = _record(req.provider, req.model, req.tag, out["in"], out["out"], False, req.key())
    return _store(req, out)


def claude_batch(reqs: list[Request], poll: int = 20) -> None:
    """Send all uncached Claude requests as one Message Batch (50% price) and cache the results."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request as BReq
    todo = {r.key(): r for r in reqs if r.provider == "anthropic" and not cached(r)}
    if not todo:
        return
    _check_cap("anthropic", estimate(list(todo.values()), batch=True))
    batch = _anthropic().messages.batches.create(
        requests=[BReq(custom_id=k, params=MessageCreateParamsNonStreaming(**_anthropic_params(r))) for k, r in todo.items()])
    print(f"  claude batch {batch.id}: {len(todo)} requests", flush=True)
    while True:
        b = _anthropic().messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        time.sleep(poll)
    for res in _anthropic().messages.batches.results(batch.id):
        r = todo.get(res.custom_id)
        if r is None:
            continue
        if res.result.type == "succeeded":
            out = _parse_anthropic(res.result.message)
            out["usd"] = _record("anthropic", r.model, r.tag, out["in"], out["out"], True, res.custom_id)
            _store(r, out)
        else:
            err = getattr(res.result, "error", None)
            print(f"  batch item {res.custom_id} {res.result.type}: {str(err)[:300]}", flush=True)  # retried next run


def _openai_body(req: Request) -> dict:
    content = [{"type": "input_text", "text": req.text}]
    if req.image:
        content.insert(0, {"type": "input_image", "image_url": f"data:image/png;base64,{_b64(req.image)}"})
    body = dict(model=req.model, instructions=req.system, reasoning={"effort": req.effort},
                input=[{"role": "user", "content": content}], max_output_tokens=req.max_tokens)
    if req.schema:
        body["text"] = {"format": {"type": "json_schema", "name": "answer", "schema": req.schema, "strict": True}}
    return body


def openai_batch(reqs: list[Request], poll: int = 20) -> None:
    """Send all uncached OpenAI requests through the Batch API (50% price), one batch per model (OpenAI rejects
    mixed-model batches), and cache the results."""
    models = sorted({r.model for r in reqs if r.provider == "openai"})
    if len(models) > 1:
        threads = [threading.Thread(target=openai_batch, args=([r for r in reqs if r.model == m], poll)) for m in models]
        [t.start() for t in threads]
        [t.join() for t in threads]
        return
    todo = {r.key(): r for r in reqs if r.provider == "openai" and not cached(r)}
    if not todo:
        return
    _check_cap("openai", estimate(list(todo.values()), batch=True))
    lines = [json.dumps({"custom_id": k, "method": "POST", "url": "/v1/responses", "body": _openai_body(r)})
             for k, r in todo.items()]
    path = ROOT / "results" / f"openai_batch_{int(time.time() * 1000)}_{threading.get_ident()}.jsonl"
    path.write_text("\n".join(lines) + "\n")
    f = _openai().files.create(file=path.open("rb"), purpose="batch")
    b = _openai().batches.create(input_file_id=f.id, endpoint="/v1/responses", completion_window="24h")
    print(f"  openai batch {b.id}: {len(todo)} requests", flush=True)
    while b.status not in ("completed", "failed", "expired", "cancelled"):
        time.sleep(poll)
        b = _openai().batches.retrieve(b.id)
    path.unlink(missing_ok=True)
    if b.status != "completed" or not b.output_file_id:
        print(f"  openai batch ended {b.status}: {b.errors}", flush=True)
    for fid in [b.output_file_id, b.error_file_id]:
        if not fid:
            continue
        for line in _openai().files.content(fid).text.splitlines():
            item = json.loads(line)
            r = todo.get(item["custom_id"])
            resp = item.get("response") or {}
            if r is None or resp.get("status_code") != 200:
                print(f"  openai batch item failed: {str(item.get('error') or resp)[:300]}", flush=True)
                continue
            body = resp["body"]
            text = "".join(c.get("text", "") for o in body.get("output", []) if o.get("type") == "message"
                           for c in o.get("content", []) if c.get("type") == "output_text")
            u = body.get("usage", {})
            out = {"text": text, "stop": body.get("status"), "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0)}
            out["usd"] = _record("openai", r.model, r.tag, out["in"], out["out"], True, item["custom_id"])
            _store(r, out)


def parse_json(text: str) -> dict | None:
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").split("\n", 1)[-1]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------- multi-turn Claude with prompt caching

CACHE_READ = {"claude-opus-5-5": 0.20, "claude-sonnet-5-5": 0.10}   # $ / 1M cached input tokens
CACHE_WRITE_MULT = 1.25                                             # 5-minute cache write = 1.25 x input


def claude_chat(model: str, system: str, messages: list[dict], effort: str, max_tokens: int, tag: str) -> dict:
    """One turn of an append-only conversation. Top-level automatic prompt caching means every earlier
    turn is billed at the cache-read price on the next call. Disk-cached by the full request."""
    key = hashlib.sha256(json.dumps([model, system, messages, effort, max_tokens], sort_keys=True).encode()).hexdigest()[:32]
    p = CACHE / f"chat_{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    _check_cap("anthropic", 0.10)
    r = _anthropic().messages.create(model=model, max_tokens=max_tokens, system=system, messages=messages,
                                     output_config={"effort": effort}, cache_control={"type": "ephemeral"})
    u = r.usage
    cr, cw = (u.cache_read_input_tokens or 0), (u.cache_creation_input_tokens or 0)
    pin, pout = PRICES[model]
    usd = (u.input_tokens * pin + cw * pin * CACHE_WRITE_MULT + cr * CACHE_READ.get(model, pin) + u.output_tokens * pout) / 1e6
    with _lock, _db() as con:
        con.execute("insert into calls values (?,?,?,?,?,?,?,?,?)",
                    (time.time(), "anthropic", model, tag, u.input_tokens + cw + cr, u.output_tokens, usd, 0, key))
    out = {"text": "".join(b.text for b in r.content if b.type == "text"), "stop": r.stop_reason,
           "in": u.input_tokens, "cache_read": cr, "cache_write": cw, "out": u.output_tokens, "usd": usd,
           "refusal": getattr(r.stop_details, "category", None) if r.stop_reason == "refusal" and r.stop_details else None}
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False))
    return out


OPENAI_CACHED_IN = {"gpt-5.5": 0.50}  # $ / 1M cached input tokens (automatic prompt caching)


def openai_chat(model: str, system: str, messages: list[dict], effort: str, max_tokens: int, tag: str) -> dict:
    """One turn of an append-only conversation on the Responses API. OpenAI caches a repeated prompt prefix
    automatically, so earlier rounds are billed at the cached-input price. Disk-cached by the full request."""
    key = hashlib.sha256(json.dumps(["oa", model, system, messages, effort, max_tokens], sort_keys=True).encode()).hexdigest()[:32]
    p = CACHE / f"chat_{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    _check_cap("openai", 0.08)
    r = _openai().responses.create(model=model, instructions=system, reasoning={"effort": effort},
                                   input=messages, max_output_tokens=max_tokens)
    u = r.usage
    cached_tok = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
    pin, pout = PRICES[model]
    usd = ((u.input_tokens - cached_tok) * pin + cached_tok * OPENAI_CACHED_IN.get(model, pin) + u.output_tokens * pout) / 1e6
    with _lock, _db() as con:
        con.execute("insert into calls values (?,?,?,?,?,?,?,?,?)",
                    (time.time(), "openai", model, tag, u.input_tokens, u.output_tokens, usd, 0, key))
    refused = any(getattr(c, "type", "") == "refusal" for o in r.output if getattr(o, "type", "") == "message"
                  for c in getattr(o, "content", []))
    out = {"text": r.output_text, "stop": "refusal" if refused else r.status, "in": u.input_tokens,
           "cache_read": cached_tok, "out": u.output_tokens, "usd": usd, "refusal": "openai_refusal" if refused else None}
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False))
    return out
