"""Playwright chromium fallback. Only used when httpx content looks too thin
to be real - never opens every page in a browser. The browser process is
started lazily on first use and reused for the rest of the run, then closed
once at the end (see close())."""
from __future__ import annotations

import logging

from signalscout.config import Settings
from signalscout.models.enums import FetchMethod
from signalscout.models.schemas import FetchResult
from signalscout.scraping.http_fetcher import USER_AGENT

logger = logging.getLogger("signalscout.browser_fetcher")


class BrowserFetcher:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._playwright = None
        self._browser = None

    def _ensure_browser(self) -> None:
        if self._browser is not None:
            return
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)

    def fetch(self, url: str) -> FetchResult:
        try:
            self._ensure_browser()
        except Exception as exc:  # e.g. chromium not installed
            logger.warning("Playwright unavailable: %s", exc)
            return FetchResult(url=url, status_code=None, html=None, error=f"playwright unavailable: {exc}", fetch_method=FetchMethod.PLAYWRIGHT)

        context = self._browser.new_context(user_agent=USER_AGENT)
        try:
            page = context.new_page()
            page.set_default_timeout(self._settings.http_timeout_seconds * 1000 * 2)
            response = page.goto(url, wait_until="domcontentloaded")
            html = page.content()
            status = response.status if response else None
            return FetchResult(url=page.url, status_code=status, html=html, error=None, fetch_method=FetchMethod.PLAYWRIGHT)
        except Exception as exc:
            return FetchResult(url=url, status_code=None, html=None, error=f"{type(exc).__name__}: {exc}", fetch_method=FetchMethod.PLAYWRIGHT)
        finally:
            context.close()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
