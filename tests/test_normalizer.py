from signalscout.ingestion.normalizer import is_same_site, normalize_url, normalized_domain


def test_normalize_url_variants_produce_same_domain():
    variants = ["https://www.example.com/", "https://example.com", "http://example.com/"]
    domains = {normalized_domain(normalize_url(v)) for v in variants}
    assert domains == {"example.com"}


def test_normalize_url_adds_scheme_when_missing():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_url_lowercases_host_and_strips_trailing_slash():
    assert normalize_url("HTTPS://Example.COM/Path/") == "https://example.com/Path"


def test_normalize_url_rejects_empty_and_unusable_input():
    assert normalize_url("") is None
    assert normalize_url("   ") is None
    assert normalize_url("not a url") is None


def test_normalized_domain_strips_www():
    assert normalized_domain("https://www.example.com/about") == "example.com"
    assert normalized_domain("https://example.com/about") == "example.com"


def test_is_same_site_matches_exact_and_subdomains():
    assert is_same_site("https://example.com/about", "example.com") is True
    assert is_same_site("https://www.example.com/about", "example.com") is True
    assert is_same_site("https://careers.example.com/jobs", "example.com") is True


def test_is_same_site_rejects_other_domains():
    assert is_same_site("https://example.org/about", "example.com") is False
    assert is_same_site("https://notexample.com/about", "example.com") is False
