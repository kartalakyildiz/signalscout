"""URL/domain normalization using only the standard library (no tldextract).

Domain handling here is intentionally simple: the "normalized domain" is the
lowercased hostname with a leading "www." stripped. This does not attempt
proper public-suffix-list resolution (e.g. it can't distinguish
"example.co.uk" registrable domains from subdomains under multi-part TLDs)
but is sufficient for a small, curated company list.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")


def _hostname_no_www(netloc: str) -> str:
    host = netloc.rsplit("@", 1)[-1]  # drop any userinfo@
    host = host.split(":", 1)[0]  # drop port
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_url(raw: str) -> str | None:
    """Returns a normalized https://host/path URL, or None if the input
    isn't a plausible URL (empty, no host, no dot in host)."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if not _SCHEME_RE.match(raw):
        raw = "https://" + raw

    parsed = urlparse(raw)
    if not parsed.netloc or "." not in parsed.netloc:
        return None

    host = _hostname_no_www(parsed.netloc)
    if not host:
        return None

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return f"{parsed.scheme.lower()}://{host}{path}"


def normalized_domain(url: str) -> str:
    """Lowercased hostname with a leading 'www.' stripped, used as the
    dedupe key and as the same-site base for page discovery."""
    parsed = urlparse(url)
    return _hostname_no_www(parsed.netloc)


def is_same_site(candidate_url: str, base_domain: str) -> bool:
    """True if candidate_url's host equals base_domain or is a subdomain of it."""
    if not base_domain:
        return False
    parsed = urlparse(candidate_url)
    host = _hostname_no_www(parsed.netloc)
    if not host:
        return False
    return host == base_domain or host.endswith("." + base_domain)
