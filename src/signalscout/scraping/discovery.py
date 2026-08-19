"""Page discovery: classify same-domain homepage links into the handful of
useful page types SignalScout looks at. Not a general-purpose crawler - this
only ever proposes at most one URL per page type, plus optional common-path
guesses when link-based discovery finds nothing.

Classification is intentionally conservative (see classify_link): it trusts
URL structure far more than link text, because link text is often prose
(article titles, descriptions) that happens to contain a category word
without the link actually being that category of page. A link is left
unclassified - rather than guessed at - whenever neither signal is strong
enough; per-category discovery is best-effort, not mandatory."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from signalscout.ingestion.normalizer import is_same_site
from signalscout.models.enums import PageType

KEYWORDS: dict[PageType, set[str]] = {
    PageType.ABOUT: {"about", "company"},
    PageType.PRODUCT: {"product", "products", "platform", "solution", "solutions", "feature", "features", "service", "services"},
    PageType.CAREERS: {"career", "careers", "job", "jobs"},
    PageType.NEWS: {"news", "blog", "press", "changelog"},
}

COMMON_PATHS: dict[PageType, list[str]] = {
    PageType.ABOUT: ["/about", "/about-us"],
    PageType.PRODUCT: ["/product", "/products", "/features"],
    PageType.CAREERS: ["/careers", "/jobs"],
    PageType.NEWS: ["/blog", "/news", "/changelog"],
}

_SKIP_PREFIXES = ("#", "mailto:", "tel:", "javascript:")
_WORD_RE = re.compile(r"[a-z0-9]+")
_MAX_LABEL_WORDS = 4  # anchor text longer than this reads as prose, not a nav label

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


def _first_path_segment_words(url: str) -> set[str]:
    """Words from only the first path segment (e.g. "changelog" from
    "/changelog/2024-01-new-feature", not "feature") - deep slug words are
    noisy and shouldn't be able to hijack a page's category."""
    path = urlparse(url).path.lower().strip("/")
    if not path:
        return set()
    first_segment = path.split("/", 1)[0]
    return set(_WORD_RE.findall(first_segment))


def _short_label_words(text: str) -> set[str]:
    """Words from anchor text, but only if it reads like a nav label
    ("About", "Careers") rather than an article title or description."""
    words = _WORD_RE.findall(text.lower())
    if not words or len(words) > _MAX_LABEL_WORDS:
        return set()
    return set(words)


def classify_link(url: str, text: str) -> PageType | None:
    """Path structure is the authoritative signal; short anchor-text labels
    are only consulted when the path itself is inconclusive. Full-sentence
    link text (article titles, descriptions) is never matched against, since
    it routinely contains category words in unrelated prose."""
    path_words = _first_path_segment_words(url)
    for page_type, keywords in KEYWORDS.items():
        if path_words & keywords:
            return page_type

    label_words = _short_label_words(text)
    if label_words:
        for page_type, keywords in KEYWORDS.items():
            if label_words & keywords:
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
