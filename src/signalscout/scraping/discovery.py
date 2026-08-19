"""Page discovery: classify same-domain homepage links into the handful of
useful page types SignalScout looks at. Not a general-purpose crawler - this
only ever proposes at most one URL per page type, plus optional common-path
guesses when link-based discovery finds nothing."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from signalscout.ingestion.normalizer import is_same_site
from signalscout.models.enums import PageType

KEYWORDS: dict[PageType, set[str]] = {
    PageType.ABOUT: {"about", "company"},
    PageType.PRODUCT: {"product", "platform", "solution", "service"},
    PageType.CAREERS: {"career", "jobs"},
    PageType.NEWS: {"news", "blog", "press"},
}

COMMON_PATHS: dict[PageType, list[str]] = {
    PageType.ABOUT: ["/about", "/about-us"],
    PageType.PRODUCT: ["/product", "/products"],
    PageType.CAREERS: ["/careers", "/jobs"],
    PageType.NEWS: ["/blog", "/news"],
}

_SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:")

DISCOVERABLE_TYPES = (PageType.ABOUT, PageType.PRODUCT, PageType.CAREERS, PageType.NEWS)


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(_SKIP_PREFIXES):
            continue
        absolute = urljoin(base_url, href)
        if not absolute.startswith(("http://", "https://")):
            continue
        links.append((absolute, a.get_text(" ", strip=True)))
    return links


def classify_link(url: str, text: str) -> PageType | None:
    haystack = f"{urlparse(url).path} {text}".lower()
    for page_type, keywords in KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return page_type
    return None


def plan_pages(homepage_url: str, homepage_html: str, base_domain: str) -> dict[PageType, str]:
    """Returns page_type -> candidate URL for whichever of the four
    discoverable types were found via same-domain homepage links. Homepage
    itself is not included here - the caller always fetches it separately."""
    plan: dict[PageType, str] = {}
    links = extract_links(homepage_html, homepage_url)
    same_site_links = [(url, text) for url, text in links if is_same_site(url, base_domain)]

    for page_type in DISCOVERABLE_TYPES:
        for url, text in same_site_links:
            if classify_link(url, text) == page_type:
                plan[page_type] = url
                break
    return plan


def common_path_candidates(homepage_url: str, page_type: PageType) -> list[str]:
    return [urljoin(homepage_url, path) for path in COMMON_PATHS.get(page_type, [])]
