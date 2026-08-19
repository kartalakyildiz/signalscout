"""httpx-based fetching with retries, timeout, and graceful failure handling.

No attempt is made to bypass website security controls: blocked/unauthorized
responses (401/403) are simply captured as a status code, not retried or
otherwise circumvented.
"""
from __future__ import annotations

import time

import httpx

from signalscout.config import Settings
from signalscout.models.enums import FetchMethod
from signalscout.models.schemas import FetchResult

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_TRANSIENT_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)


def fetch_url(client: httpx.Client, url: str, settings: Settings) -> FetchResult:
    last_error: str | None = None
    for attempt in range(settings.http_max_retries + 1):
        try:
            response = client.get(url, timeout=settings.http_timeout_seconds)
            return FetchResult(
                url=str(response.url),
                status_code=response.status_code,
                html=response.text,
                error=None,
                fetch_method=FetchMethod.HTTPX,
            )
        except _TRANSIENT_EXCEPTIONS as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        except httpx.HTTPError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            break  # non-transient (e.g. TooManyRedirects) - no point retrying

        if attempt < settings.http_max_retries:
            time.sleep(0.5 * (attempt + 1))

    return FetchResult(url=url, status_code=None, html=None, error=last_error or "unknown fetch error", fetch_method=FetchMethod.HTTPX)


def build_client() -> httpx.Client:
    return httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT})
