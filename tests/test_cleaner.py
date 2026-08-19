from signalscout.scraping.cleaner import clean_html
from tests.fixtures.sample_pages import NOISY_HOMEPAGE_HTML, THIN_JS_SHELL_HTML


def test_clean_html_strips_script_and_style_noise():
    cleaned = clean_html(NOISY_HOMEPAGE_HTML)
    assert "console.log" not in cleaned.text
    assert "color: red" not in cleaned.text


def test_clean_html_keeps_meaningful_content():
    cleaned = clean_html(NOISY_HOMEPAGE_HTML)
    assert "Acme Corp is hiring a Head of AI" in cleaned.text
    assert "Founded in 2010" in cleaned.text
    assert "Offices in Austin and Berlin" in cleaned.text


def test_clean_html_extracts_title():
    cleaned = clean_html(NOISY_HOMEPAGE_HTML)
    assert cleaned.title == "Acme Corp - Home"


def test_clean_html_collapses_whitespace():
    cleaned = clean_html(NOISY_HOMEPAGE_HTML)
    assert "  " not in cleaned.text
    assert "\n\n" not in cleaned.text


def test_clean_html_on_js_only_shell_yields_thin_content():
    cleaned = clean_html(THIN_JS_SHELL_HTML)
    assert len(cleaned.text) < 50


def test_clean_html_handles_empty_input():
    cleaned = clean_html("")
    assert cleaned.title == ""
    assert cleaned.text == ""
    assert clean_html(None).text == ""
