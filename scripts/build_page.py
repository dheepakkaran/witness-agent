"""Build the GitHub Pages site docs/index.html. Every number comes from film/data.js (written by
film/make_film.py data from results/), so the page, the film and RESULTS.md always agree.

    .venv/bin/python film/make_film.py data && .venv/bin/python scripts/build_page.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "film" / "data.js").read_text().split("const DATA = ", 1)[1].rstrip().rstrip(";"))
T = D["targets"]

CLAY, GREEN, VIOLET, TEAL, AMBER, RED = "#ec8a5c", "#5fd39a", "#a08cff", "#3fe0c5", "#ffb547", "#ff4d5e"


def bot(color, view=None, w=84):
    acc = ""
    if view == "raw":
        acc = (f'<rect x="-48" y="-26" width="40" height="34" rx="8" fill="none" stroke="{color}" stroke-width="4"/>'
               f'<rect x="8" y="-26" width="40" height="34" rx="8" fill="none" stroke="{color}" stroke-width="4"/>'
               f'<line x1="-8" y1="-12" x2="8" y2="-12" stroke="{color}" stroke-width="4"/>')
    elif view == "img":
        acc = (f'<rect x="30" y="-100" width="54" height="40" rx="9" fill="#11131a" stroke="{color}" stroke-width="4"/>'
               f'<circle cx="57" cy="-80" r="11" fill="none" stroke="{color}" stroke-width="4"/>')
    elif view == "ta":
        acc = (f'<path d="M58 -110 h70 a16 16 0 0 1 16 16 v34 a16 16 0 0 1 -16 16 h-44 l-18 16 v-16 h-8 a16 16 0 0 1 -16 -16 v-34 a16 16 0 0 1 16 -16z" '
               f'fill="#11131a" stroke="{color}" stroke-width="4"/><text x="93" y="-66" text-anchor="middle" font-size="34" fill="{color}">அ</text>')
    return (f'<svg class="bot" width="{w}" height="{w}" viewBox="-110 -125 240 250" aria-hidden="true"><g>'
            f'<line x1="0" y1="-86" x2="0" y2="-60" stroke="{color}" stroke-width="5" stroke-linecap="round"/><circle cx="0" cy="-92" r="9" fill="{color}"/>'
            f'<rect x="-78" y="-62" width="156" height="150" rx="44" fill="#11131a" stroke="{color}" stroke-width="5"/>'
            f'<rect x="-56" y="-38" width="112" height="78" rx="24" fill="#05060a"/>'
            f'<rect class="eye" x="-34" y="-18" width="18" height="30" rx="9" fill="#f4efe4"/><rect class="eye" x="16" y="-18" width="18" height="30" rx="9" fill="#f4efe4"/>'
            f'<rect x="-22" y="62" width="44" height="8" rx="4" fill="{color}" opacity=".55"/>{acc}</g></svg>')


GLITCH = ('<svg class="bot glitch" width="96" height="96" viewBox="-130 -160 260 320" aria-hidden="true">'
          '<path d="M0 -150 C 70 -150 110 -60 118 40 C 124 110 90 140 0 140 C -90 140 -124 110 -118 40 C -110 -60 -70 -150 0 -150Z" fill="#1a0b10" stroke="#ff4d5e" stroke-width="6"/>'
          '<path d="M-70 -20 C -50 -80 50 -80 70 -20 C 60 40 -60 40 -70 -20Z" fill="#050205"/><rect x="-46" y="-26" width="92" height="12" rx="6" fill="#ff4d5e"/>'
          '<path d="M-30 30 Q 0 46 30 30" stroke="#ff4d5e" stroke-width="5" fill="none" stroke-linecap="round" opacity=".7"/></svg>')


def tiles(key):
    return "".join(f'<i class="{"x" if w else "s"}" title="scenario {j + 1}: {"attacker won in round " + str(T[key]["win_round"][j]) if w else "held for 5 rounds"}"></i>'
                   for j, w in enumerate(T[key]["won"]))


ROWS = [("T3b_nano", "GPT-5.4 nano", "alone", GREEN), ("T3c_qwen", "Qwen 3.8 27B", "alone", VIOLET), ("T3a_haiku", "Claude Haiku 5.5", "alone", CLAY),
        ("T1_single", "Claude Opus 5.5", "alone", CLAY), ("T4_weak_all_flag", "Weak team", "7 witnesses must agree", TEAL),
        ("T2_all_flag", "Strong team", "9 witnesses must agree", TEAL)]
score = "".join(f'''<div class="srow"><div class="slab" style="color:{c}">{n}<small>{sub}</small></div><div class="tiles">{tiles(k)}</div>
<div class="scnt" style="color:{RED if T[k]["k"] else TEAL}">{T[k]["k"]}/{T[k]["n"]}<small>95% CI {round(100 * T[k]["ci"][0])}–{round(100 * T[k]["ci"][1])}%</small></div></div>''' for k, n, sub, c in ROWS)

hr, ht = D["haiku_raw"], D["haiku_ta"]
pct = lambda a: f"{100 * a[0] / a[1]:.0f}%"

html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Witness Agent</title>
<meta name="description" content="A pre-registered agent-security experiment: when several AI readers have to agree before an agent acts, does a defence-aware attacker fool them together? 16 witnesses, 12 scenarios, {D['rounds']} adaptive attack rounds.">
<meta property="og:title" content="Witness: do AI readers that check each other fail together?">
<meta property="og:image" content="media/witness.jpg">
<style>
@font-face{{font-family:Inter;src:url(fonts/InterVariable.woff2) format("woff2");font-weight:100 900;font-display:swap}}
@font-face{{font-family:Serif;src:url(fonts/InstrumentSerif-Regular.woff2) format("woff2");font-display:swap}}
@font-face{{font-family:Serif;font-style:italic;src:url(fonts/InstrumentSerif-Italic.woff2) format("woff2");font-display:swap}}
@font-face{{font-family:Mono;src:url(fonts/JetBrainsMono-Regular.woff2) format("woff2");font-display:swap}}
:root{{--bg:#06070b;--panel:#0d0f15;--panel2:#141720;--line:#22252f;--text:#f4efe4;--muted:#9a9ea9;--faint:#6b6f7a;
  --amber:#ffb547;--teal:#3fe0c5;--red:#ff4d5e;--paper:#f3eee2;--ink:#1d1b17}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{--bg:#fbf9f4;--panel:#fff;--panel2:#f2efe7;--line:#e4dfd3;--text:#16140f;--muted:#5d5a52;--faint:#8b877d;
  --amber:#c27a07;--teal:#0f9e86;--red:#d4283c}}}}
:root[data-theme="dark"]{{--bg:#06070b;--panel:#0d0f15;--panel2:#141720;--line:#22252f;--text:#f4efe4;--muted:#9a9ea9;--faint:#6b6f7a;--amber:#ffb547;--teal:#3fe0c5;--red:#ff4d5e}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:var(--amber);text-decoration:none}}a:hover{{text-decoration:underline}}
code{{font:13.5px/1.5 Mono,ui-monospace,monospace;background:var(--panel2);padding:1px 6px;border-radius:5px}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 16px}}
nav{{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 84%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}}
nav .wrap{{display:flex;gap:20px;align-items:center;height:54px;overflow-x:auto;white-space:nowrap}}
nav b{{font:400 24px Serif;margin-right:auto;letter-spacing:-.01em}}
nav a{{color:var(--muted);font-size:14px}}
header{{padding:76px 0 6px;text-align:center}}
.eyebrow{{font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--muted);font-weight:600}}
h1{{font:400 clamp(48px,9vw,96px)/1 Serif;letter-spacing:-.02em;margin:16px 0 14px}}
h1 em,h2 em{{color:var(--amber)}}
.lede{{max-width:680px;margin:0 auto;color:var(--muted);font-size:18px}}
.links{{margin:26px 0 0;display:flex;gap:10px;justify-content:center;flex-wrap:wrap}}
.btn{{display:inline-block;padding:9px 16px;border:1px solid var(--line);border-radius:999px;color:var(--text);font-size:14px;background:var(--panel)}}
.btn:hover{{text-decoration:none;border-color:var(--amber)}}
.film{{margin:44px 0 0;border:1px solid var(--line);border-radius:16px;background:#000;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.35)}}
.film video{{display:block;width:100%;height:auto;aspect-ratio:16/9}}
.film figcaption{{padding:12px 16px;font-size:13px;color:var(--muted);background:var(--panel);border-top:1px solid var(--line)}}
section{{padding:72px 0 0}}
h2{{font:400 clamp(34px,5vw,48px)/1.08 Serif;letter-spacing:-.015em;margin:0 0 12px}}
.sub{{color:var(--muted);margin:0 0 26px;max-width:740px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:40px 0 0}}
.kpi{{border:1px solid var(--line);border-radius:14px;padding:18px;background:var(--panel)}}
.kpi .v{{font:400 46px/1 Serif;letter-spacing:-.01em}}
.kpi .l{{font-size:13.5px;color:var(--muted);margin-top:8px}}
.story{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}
.step{{border:1px solid var(--line);border-radius:14px;padding:20px;background:var(--panel)}}
.step .n{{font:600 12px Inter;letter-spacing:.2em;color:var(--faint)}}
.step h3{{margin:8px 0 6px;font-size:18px}}
.step p{{margin:0;color:var(--muted);font-size:14.5px}}
.cast{{display:flex;flex-wrap:wrap;gap:12px}}
.who{{flex:1 1 150px;border:1px solid var(--line);border-radius:14px;padding:14px 10px;text-align:center;background:var(--panel)}}
.who .nm{{font-weight:650;font-size:14.5px;margin-top:4px}}
.who .ds{{font-size:12.5px;color:var(--muted)}}
.bot .eye{{transform-box:fill-box;transform-origin:center;animation:blink 4.2s infinite}}
.who:nth-child(2n) .bot .eye{{animation-delay:1.3s}} .who:nth-child(3n) .bot .eye{{animation-delay:2.4s}}
@keyframes blink{{0%,94%,100%{{transform:scaleY(1)}}96%{{transform:scaleY(.1)}}}}
.glitch{{animation:sway 3s ease-in-out infinite}}@keyframes sway{{50%{{transform:translateX(5px) rotate(2deg)}}}}
.board{{border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:18px 18px 8px}}
.srow{{display:grid;grid-template-columns:200px 1fr 100px;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}}
.srow:last-child{{border-bottom:0}}
.slab{{font-weight:650;font-size:15px}}.slab small{{display:block;font-weight:500;color:var(--muted);font-size:12.5px}}
.tiles{{display:grid;grid-template-columns:repeat(12,1fr);gap:5px}}
.tiles i{{aspect-ratio:1;border-radius:6px;display:block}}
.tiles i.x{{background:var(--red)}}
.tiles i.s{{background:color-mix(in srgb,var(--teal) 16%,transparent);border:1.5px solid color-mix(in srgb,var(--teal) 55%,transparent)}}
.scnt{{text-align:right;font:400 30px/1 Serif}}.scnt small{{display:block;font:500 11px Inter;color:var(--faint);margin-top:4px}}
.legend{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:10px 2px 0}}
.legend span::before{{content:"";display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px;background:var(--c)}}
.split{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
.panel{{border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:22px}}
.big{{font:400 72px/1 Serif}}
.bar{{height:14px;border-radius:7px;background:var(--panel2);overflow:hidden;margin:6px 0 14px}}.bar i{{display:block;height:100%;border-radius:7px}}
.blab{{display:flex;justify-content:space-between;font-size:14px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}}th{{color:var(--muted);font-weight:600;font-size:12.5px;letter-spacing:.04em}}
.papers{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.paper{{background:var(--paper);color:var(--ink);border-radius:6px;padding:16px 18px;box-shadow:0 14px 30px rgba(0,0,0,.25);transform:rotate(var(--r))}}
.paper b{{font:400 22px/1.15 Serif;display:block;margin:6px 0}}.paper small{{font:12px Mono;color:#7a7466}}.paper p{{font:italic 15px/1.35 Serif;color:#5d5546;margin:8px 0 0}}
.chips span{{display:inline-block;margin:0 8px 8px 0;padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--panel);font-size:14px}}
footer{{padding:72px 0 56px;color:var(--faint);font-size:13px;text-align:center}}
@media (max-width:640px){{.srow{{grid-template-columns:1fr 70px}}.tiles{{grid-column:1/-1;grid-row:2}}.big{{font-size:56px}}}}
</style>
</head>
<body>
<nav><div class="wrap"><b>Witness</b><a href="#film">Film</a><a href="#idea">Idea</a><a href="#results">Results</a><a href="#twist">Twist</a><a href="#method">Method</a><a href="#limits">Limits</a></div></nav>
<div class="wrap">
<header>
  <div class="eyebrow">Agent security · pre-registered experiment · November 2026</div>
  <h1>Witness</h1>
  <p class="lede">An AI agent reads an invoice and pays the IBAN on it. One hidden line can change a few digits. If several AI <em>witnesses</em> must agree before the agent acts, does an attacker who knows the defence still get through? And do the witnesses fail together?</p>
  <div class="links"><a class="btn" href="#results">The results</a><a class="btn" href="#method">How it was tested</a></div>
</header>

<figure class="film" id="film">
  <video controls playsinline preload="metadata" poster="media/witness.jpg"><source src="media/witness.mp4" type="video/mp4"></video>
  <figcaption>The 132-second film. Rendered frame by frame from <code>film/witness.html</code>; every number on screen is read from the result files.</figcaption>
</figure>

<div class="kpis">
  <div class="kpi"><div class="v" style="color:var(--red)">{T['T3b_nano']['k']}/{T['T3b_nano']['n']}</div><div class="l">scenarios where the attacker beat GPT-5.4 nano on its own</div></div>
  <div class="kpi"><div class="v" style="color:var(--teal)">{T['T4_weak_all_flag']['k']}/{T['T4_weak_all_flag']['n']}</div><div class="l">for a team of weak models that must all agree</div></div>
  <div class="kpi"><div class="v">{D['pg2_caught']}/{D['pg2_n']}</div><div class="l">static attacks caught by Prompt Guard 2, a standard detector; the witness flag sent {D['flag_escalated']}/{D['static_docs']} to a human</div></div>
  <div class="kpi"><div class="v" style="color:var(--amber)">{D['cascade_pct']}%</div><div class="l">of the cost of asking every witness, when the check stops at the first doubt</div></div>
</div>

<section id="idea">
  <h2>The idea, <em>in four steps</em></h2>
  <p class="sub">A court trusts a fact more when independent witnesses agree. The same idea is used here for an AI agent that handles money.</p>
  <div class="story">
    <div class="step"><div class="n">01 · THE THREAT</div><h3>A near-target change</h3><p>The attacker can't touch the real invoice text. It adds a block (hidden text, a fake "correction", a forged audit trail) that tries to make the agent report an IBAN, amount, date, phone, link or email a few characters off.</p></div>
    <div class="step"><div class="n">02 · THE WITNESSES</div><h3>Read it several ways</h3><p>Different models (Claude, GPT, Qwen; strong and small) read the same document as raw HTML, as a screenshot, or as a Tamil translation, and each reports the value plus a conflict flag.</p></div>
    <div class="step"><div class="n">03 · THE RULE</div><h3>All agree, or ask</h3><p>The agent acts only if every witness gives the same value and none flags a conflict. Any doubt and it asks the human. The check runs as a cascade: cheapest witness first, stop at the first doubt.</p></div>
    <div class="step"><div class="n">04 · THE ATTACKER</div><h3>It knows everything</h3><p>GPT-5.5 plays the attacker. It sees the witness list, prompts and rule, gets every answer back, and has 5 rounds per scenario. A pixel check stops it from covering the real value.</p></div>
  </div>
</section>

<section>
  <h2>The cast</h2>
  <p class="sub">Strong models are drawn big, small models small. Colours: Claude clay, GPT green, Qwen violet.</p>
  <div class="cast">
    <div class="who">{GLITCH}<div class="nm" style="color:var(--red)">Glitch</div><div class="ds">the attacker · GPT-5.5</div></div>
    <div class="who">{bot(CLAY)}<div class="nm">Claude Opus 5.5</div><div class="ds">strong</div></div>
    <div class="who">{bot(GREEN)}<div class="nm">GPT-5.5</div><div class="ds">strong</div></div>
    <div class="who">{bot(CLAY, w=64)}<div class="nm">Claude Haiku 5.5</div><div class="ds">small</div></div>
    <div class="who">{bot(GREEN, w=64)}<div class="nm">GPT-5.4 nano</div><div class="ds">small</div></div>
    <div class="who">{bot(VIOLET, w=64)}<div class="nm">Qwen 3.8 27B</div><div class="ds">open weights</div></div>
  </div>
  <div class="cast" style="margin-top:12px">
    <div class="who">{bot(TEAL, "raw")}<div class="nm">Raw view</div><div class="ds">reads the HTML source, hidden text included</div></div>
    <div class="who">{bot(TEAL, "img")}<div class="nm">Screenshot view</div><div class="ds">reads only what a human sees</div></div>
    <div class="who">{bot(TEAL, "ta")}<div class="nm">Tamil view</div><div class="ds">reads a Tamil translation of the whole document</div></div>
  </div>
</section>

<section id="results">
  <h2>Alone they fall. <em>Together they held.</em></h2>
  <p class="sub">Each tile is one scenario: 5 adaptive attack rounds against that defence. Red: the defence accepted the attacker's value at least once. Shield: it held all 5 rounds.</p>
  <div class="board">{score}
    <div class="legend"><span style="--c:var(--red)">attacker won</span><span style="--c:var(--teal)">defence held</span><span>Wilson 95% intervals · 12 scenarios each</span></div>
  </div>
  <div class="split" style="margin-top:14px">
    <div class="panel"><div class="eyebrow">Static attacks</div><div class="big">{D['strong_fooled']}<span style="font-size:32px;color:var(--muted)"> / {D['strong_reads']}</span></div><p class="sub" style="margin:8px 0 0">strong-model reads fooled by six classic injection styles (hidden CSS, white text, HTML comments, alt text, a visible note to AI, a fake update box).</p></div>
    <div class="panel"><div class="eyebrow">Transfer upward</div><div class="big">{D['transfer_opus']}<span style="font-size:32px;color:var(--muted)"> / {D['transfer_src']}</span></div><p class="sub" style="margin:8px 0 0">adaptive snippets that fooled a small model and also fooled Claude Opus 5.5.</p></div>
  </div>
</section>

<section id="twist">
  <h2>The twist: <em>our prediction was wrong</em></h2>
  <p class="sub">We pre-registered that changing the <b>view</b> (raw / screenshot / Tamil) would make witnesses fail more independently than changing the <b>company</b>. The data said the opposite. φ measures how often two witnesses are fooled together (0 = independent, 1 = always together).</p>
  <div class="panel">
    <div class="blab"><span>Same model, different view · small models</span><b style="color:var(--amber)">φ = {D['phi_weak_view']:.2f}</b></div><div class="bar"><i style="width:{D['phi_weak_view'] * 100:.0f}%;background:var(--amber)"></i></div>
    <div class="blab"><span>Different company, same view · small models</span><b style="color:var(--teal)">φ = {D['phi_weak_vendor']:.2f}</b></div><div class="bar"><i style="width:{D['phi_weak_vendor'] * 100:.0f}%;background:var(--teal)"></i></div>
    <div class="blab"><span>Same model, different view · strong models</span><b style="color:var(--amber)">φ = {D['phi_strong_view']:.2f}</b></div><div class="bar"><i style="width:{D['phi_strong_view'] * 100:.0f}%;background:var(--amber)"></i></div>
    <div class="blab"><span>Different company, same view · strong models</span><b style="color:var(--teal)">φ = {D['phi_strong_vendor']:.2f}</b></div><div class="bar"><i style="width:{D['phi_strong_vendor'] * 100:.0f}%;background:var(--teal)"></i></div>
    <p class="sub" style="margin:6px 0 0">And the Tamil view hurt: Claude Haiku was fooled on {pct(ht)} of adaptive snippets in Tamil against {pct(hr)} on the raw HTML. For a safety ensemble, mix vendors before you mix views.</p>
  </div>
</section>

<section id="method">
  <h2>How it was tested</h2>
  <p class="sub">The plan and hypotheses were committed before any test call (<code>PREREG.md</code>, then <code>EXTENSION.md</code> for the small models); every deviation is written down.</p>
  <table>
    <tr><th>Part</th><th>What</th></tr>
    <tr><td>Documents</td><td>12 synthetic scenarios (invoices, statements, meeting invites, support pages, payment links, remittance emails) with valid IBAN checksums; fictional companies</td></tr>
    <tr><td>Witnesses</td><td>16: Claude Opus 5.5, GPT-5.5, Qwen 3.8 27B, Claude Haiku 5.5, GPT-5.4 nano × raw / screenshot / Tamil views, plus two Opus prompt variants</td></tr>
    <tr><td>Attacker</td><td>GPT-5.5 (reasoning low), defence-aware, 5 rounds × 12 scenarios × 6 targets = {D['rounds']} rounds; {D['invalid']} were thrown out by the snippet rules ({D['pixel']} by the pixel check)</td></tr>
    <tr><td>Evaluation</td><td>Every valid snippet re-read by every witness: {D['reads']:,} reads over {D['snippets']} snippets, through the batch APIs</td></tr>
    <tr><td>Cost control</td><td>Batch APIs (−50%), prompt caching for the attacker, low effort, an early-exit cascade, hard caps per provider. Total: Claude ${D['usd_claude']:.2f}, OpenAI ${D['usd_openai']:.2f}</td></tr>
    <tr><td>Infra</td><td>Qwen on the Groq free tier, then on an own vLLM server (A100 80GB) when the free tier stalled; {D['qwen_agree'][0]}/{D['qwen_agree'][1]} same answers on a serving check</td></tr>
  </table>
</section>

<section>
  <h2>What it builds on</h2>
  <p class="sub">The 2026 papers read before the design. This study adds a measurement none of them made: correlated failure across models and views under a defence-aware attacker.</p>
  <div class="papers">
    <div class="paper" style="--r:-1deg"><small>arXiv 2510.09023</small><b>The Attacker Moves Second</b><p>Defences must be tested against adaptive attackers.</p></div>
    <div class="paper" style="--r:.8deg"><small>arXiv 2610.32531 · NTBench</small><b>Near-target prompt injection</b><p>Small, plausible changes slip past defences.</p></div>
    <div class="paper" style="--r:-.6deg"><small>arXiv 2609.36121 · Pictionary</small><b>Render Before Reading</b><p>Models obey text in images less.</p></div>
    <div class="paper" style="--r:1deg"><small>arXiv 2509.24967</small><b>SecInfer</b><p>One model, many prompts, then vote.</p></div>
    <div class="paper" style="--r:-.9deg"><small>arXiv 2512.06716</small><b>SIEVE</b><p>Verify selectively, escalate the rest.</p></div>
    <div class="paper" style="--r:.5deg"><small>arXiv 2503.18813 · CaMeL</small><b>Defeating Prompt Injections by Design</b><p>Keep untrusted data away from actions.</p></div>
  </div>
</section>

<section id="limits">
  <h2>Honest limits</h2>
  <div class="chips"><span>12 scenarios: only large gaps are clear</span><span>Synthetic documents</span><span>Claude Opus 5.5 refused to play the attacker (cyber safety category), so GPT-5.5 attacked</span><span>Strong model alone and strong team both 0/12: this test cannot separate them</span><span>Qwen partly served by our own vLLM; it was fooled less there than on Groq</span><span>The attacker ran at low reasoning effort</span></div>
</section>
</div>
<footer>Witness Agent · pre-registered November 2026 · numbers from <code>RESULTS.md</code></footer>
</body>
</html>
'''
(ROOT / "docs" / "index.html").write_text(html)
print("docs/index.html", len(html) // 1024, "KB")
