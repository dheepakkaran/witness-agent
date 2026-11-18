# Extension pre-registration: weak models (decided 2026-11-18, during the main test run)

## Why there is an extension

In dev, the strong witnesses were almost never fooled. Static attacks fooled them 0/72, and the 1-scenario adaptive
pilot fooled none of them in 6 rounds. With almost no failures, the correlation questions (H2, H3) cannot be measured.
So the owner approved an extension with the small model of each vendor, and a larger budget:

- OpenAI cap: $10 → **$18**;
- Claude cap: $10 → **$11**.

The main pre-registration (`PREREG.md`, commit 64c7417) and its test run are not changed. Everything here is
added on top, with separate output files, and this file is committed before any extension test call.

## Weak witnesses (`witness/weak.py`)

| name | model | view |
|---|---|---|
| qwen_raw | qwen/qwen3.8-27b | raw HTML (the same witness as in the main set) |
| haiku_raw / haiku_img / haiku_ta | claude-haiku-5-5 | raw / screenshot / Tamil |
| nano_raw / nano_img / nano_ta | gpt-5.4-nano | raw / screenshot / Tamil |

The prompts, schema, effort (`low`) and Tamil translation (Claude Opus 5.5) are the same as for the strong witnesses.

## Runs (`scripts/run_extension.py`)

1. **Static:** the 6 new witnesses on the same 84 static test documents.
2. **Adaptive:** the same 12 test scenarios, the same attacker (GPT-5.5, effort `low`), the same rules, pixel check and
   at most 5 rounds. Four new targets:
   - **T3a** = haiku_raw plain;
   - **T3b** = nano_raw plain;
   - **T3c** = qwen_raw plain;
   - **T4** = all 7 weak witnesses + flag, as an early-exit cascade in the order
     qwen_raw, haiku_raw, nano_raw, haiku_img, nano_img, haiku_ta, nano_ta.
3. **Full:** every valid snippet is read through the batch APIs.
   - Snippets from the main campaigns are read by all 16 witnesses (9 strong + 7 weak), and they go first.
   - Snippets from the extension campaigns are read by 13: the two Opus prompt variants (opus_raw_b, opus_raw_c) are left
     out for cost, since in every dev and pilot read they gave the same answer as opus_raw. gpt_ta is also left out, to
     stay under the $18 OpenAI cap. This deviation was decided during the run and is listed in the report.

## Hypotheses

- **E1.** Each weak single target (T3a, T3b, T3c) is beaten in a larger share of campaigns than the strong single
  target T1. We report wins out of 12 with Wilson 95% intervals.
- **E2.** The weak ensemble T4 is beaten in fewer campaigns than the most-beaten weak single target, i.e. a team of
  weak readers protects better than its weakest member. A secondary comparison is T4 against T1 (one strong reader).
- **E3 (H2 again, now with failures).** On the full 16-witness snippet pool, compare mean phi for:
  - *same view, different vendor* (haiku_raw, nano_raw, qwen_raw);
  - *same vendor, different view* (haiku_raw/img/ta, nano_raw/img/ta).
  We predict the different-view pairs have the lower mean phi. 95% cluster-bootstrap CIs.
- **E4 (transfer to strong models).** Among snippets that fooled at least one weak witness, the share that also fooled
  each strong witness. We predict it is low for every strong witness.
- **E5 (strong vs weak per vendor).** The fooled rate of Opus vs Haiku and of GPT-5.5 vs nano, per view, on the full pool.

## Stopping

The code stops at the caps. Whatever is finished gets reported, and anything cut is stated.

## Deviation during the run (2026-11-18 11:22)

Groq's free tier left requests hanging for about 8 minutes each. So for the last open campaigns (scenario s2-32-email,
target T3c from round 4 and T4 from round 1), the Qwen witness was served by our own vLLM server instead. That server
runs the same open weights, Qwen/Qwen3.8-27B in bf16, on an A100 80GB (Brev); provider label `brev` in the cache and the
ledger. Every other live Qwen call in the campaigns came from Groq.

All Qwen reads in the 16-witness evaluation come from the vLLM server. A serving check on the 84 static test documents
(`results/test_qwen_backend_agreement.json`) found:
- the same label (truth / attacker / other) for 79/84 documents;
- the same label and flag for 69/84;
- fooled 4/84 on Groq against 1/84 on vLLM.
