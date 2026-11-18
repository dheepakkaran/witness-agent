"""Extension (EXTENSION.md): seven weak witnesses, the small model of each vendor in each view.

Kept apart from `witnesses.py` so the pre-registered witness set stays unchanged. Same prompts, same
schema, same Tamil translation (by Claude Opus 5.5) as the strong witnesses.
"""
from __future__ import annotations

from .witnesses import BY_NAME, PROVIDER, Witness

HAIKU, NANO = "claude-haiku-5-5", "gpt-5.4-nano"
PROVIDER[HAIKU] = "anthropic"
PROVIDER[NANO] = "openai"

WEAK = [
    Witness("qwen_raw", "qwen/qwen3.8-27b", "raw", "base"),   # already a strong-set member; reused, same requests
    Witness("haiku_raw", HAIKU, "raw", "base"),
    Witness("nano_raw", NANO, "raw", "base"),
    Witness("haiku_img", HAIKU, "img", "base"),
    Witness("nano_img", NANO, "img", "base"),
    Witness("haiku_ta", HAIKU, "ta", "base"),
    Witness("nano_ta", NANO, "ta", "base"),
]
NEW = [w for w in WEAK if w.name != "qwen_raw"]
for w in NEW:
    BY_NAME[w.name] = w
