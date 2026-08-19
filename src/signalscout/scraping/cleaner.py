"""Reusable HTML -> cleaned text extraction. Strips script/style/noscript and
obvious repetitive navigation, keeps title/headings/paragraphs/list text, and
normalizes whitespace."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from signalscout.models.schemas import CleanedPage

_STRIP_TAGS = ["script", "style", "noscript", "svg", "iframe", "template", "nav", "footer"]
_CONTENT_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]
_WHITESPACE_RE = re.compile(r"[ \t\xa0]+")
_BLANK_LINES_RE = re.compile(r"\n{2,}")


def clean_html(html: str | None) -> CleanedPage:
    if not html or not html.strip():
        return CleanedPage(title="", text="")

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    parts: list[str] = [title] if title else []
    for el in soup.find_all(_CONTENT_TAGS):
        text = el.get_text(" ", strip=True)
        if text:
            parts.append(text)

    combined = "\n".join(parts)
    combined = _WHITESPACE_RE.sub(" ", combined)
    combined = _BLANK_LINES_RE.sub("\n", combined)
    return CleanedPage(title=title, text=combined.strip())
