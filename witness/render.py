"""Render HTML to a PNG screenshot (what a human sees) and to visible text."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / "workspace/.tools/ms-playwright"))

from playwright.sync_api import sync_playwright  # noqa: E402

CACHE = Path(__file__).resolve().parent.parent / "results" / "renders"


class Renderer:
    def __init__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": 880, "height": 600}, device_scale_factor=1)
        CACHE.mkdir(parents=True, exist_ok=True)

    def png(self, html: str) -> Path:
        key = hashlib.sha256(html.encode()).hexdigest()[:24]
        out = CACHE / f"{key}.png"
        if not out.exists():
            self._page.set_content(html, wait_until="load")
            self._page.screenshot(path=str(out), full_page=True)
        return out

    def visible_text(self, html: str) -> str:
        self._page.set_content(html, wait_until="load")
        return self._page.inner_text("body")

    def close(self):
        self._browser.close()
        self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
