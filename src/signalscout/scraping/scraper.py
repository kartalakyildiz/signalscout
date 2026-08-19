"""Orchestrates discovery + httpx fetch (+ Playwright fallback) + cleaning
for a single company. This is the only module that ties the other scraping
submodules together."""
from __future__ import annotations

import hashlib
import logging

from signalscout.config import Settings
from signalscout.ingestion.csv_loader import CompanyInput
from signalscout.models.enums import PageType
from signalscout.models.schemas import CleanedPage, ScrapedPage
from signalscout.scraping import discovery, http_fetcher
from signalscout.scraping.browser_fetcher import BrowserFetcher
from signalscout.scraping.cleaner import clean_html

logger = logging.getLogger("signalscout.scraper")


def _hash_text(text: str) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_page(client, browser_fetcher: BrowserFetcher | None, url: str, page_type: PageType, settings: Settings) -> tuple[ScrapedPage, str | None]:
    fetch_result = http_fetcher.fetch_url(client, url, settings)
    html = fetch_result.html
    cleaned: CleanedPage = clean_html(html)

    is_success = fetch_result.status_code is not None and 200 <= fetch_result.status_code < 300
    if browser_fetcher is not None and is_success and len(cleaned.text) < settings.min_content_chars:
        logger.info("Thin content (%d chars) at %s, falling back to Playwright", len(cleaned.text), url)
        pw_result = browser_fetcher.fetch(url)
        if pw_result.html:
            pw_cleaned = clean_html(pw_result.html)
            if len(pw_cleaned.text) > len(cleaned.text):
                fetch_result = pw_result
                html = pw_result.html
                cleaned = pw_cleaned
                logger.info("Playwright fallback improved content for %s (%d chars)", url, len(cleaned.text))

    final_success = fetch_result.status_code is not None and 200 <= fetch_result.status_code < 300
    if final_success and cleaned.text:
        error = None
    elif not final_success:
        error = fetch_result.error or (
            f"HTTP {fetch_result.status_code}" if fetch_result.status_code is not None else "fetch failed"
        )
    else:
        error = "no content extracted"

    scraped = ScrapedPage(
        page_type=page_type,
        url=fetch_result.url or url,
        fetch_method=fetch_result.fetch_method,
        http_status=fetch_result.status_code,
        title=cleaned.title,
        cleaned_text=cleaned.text,
        content_hash=_hash_text(cleaned.text),
        error=error,
    )
    return scraped, html


def scan_company(company: CompanyInput, settings: Settings, browser_fetcher: BrowserFetcher | None) -> list[ScrapedPage]:
    pages: list[ScrapedPage] = []

    with http_fetcher.build_client() as client:
        homepage_page, homepage_html = _fetch_page(client, browser_fetcher, company.website, PageType.HOMEPAGE, settings)
        pages.append(homepage_page)

        if not homepage_html:
            logger.warning("Homepage unavailable for %s (%s) - skipping page discovery", company.name, company.website)
            return pages

        plan = discovery.plan_pages(company.website, homepage_html, company.normalized_domain)

        for page_type in discovery.DISCOVERABLE_TYPES:
            candidate_url = plan.get(page_type)
            if candidate_url:
                scraped, _ = _fetch_page(client, browser_fetcher, candidate_url, page_type, settings)
                pages.append(scraped)
                continue

            for guess_url in discovery.common_path_candidates(company.website, page_type):
                scraped, _ = _fetch_page(client, browser_fetcher, guess_url, page_type, settings)
                if scraped.error is None:
                    pages.append(scraped)
                    break
            else:
                logger.info("No %s page found for %s", page_type.value, company.name)

    return pages
