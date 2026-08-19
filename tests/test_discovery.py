from signalscout.models.enums import PageType
from signalscout.scraping.discovery import classify_link, plan_pages

# --- Regression cases from the real run that revealed the bug -------------


def test_changelog_article_is_news_not_about():
    # Linear-style: a changelog entry whose slug/title happens to mention
    # the company/product in prose must not be classified as "about".
    url = "https://linear.app/changelog/2024-01-15-improved-triage-for-your-company"
    text = "Improved triage flow makes it easier for your company to ship"
    assert classify_link(url, text) == PageType.NEWS


def test_message_streams_page_is_not_about():
    # Postmark-style: "about" appearing as an ordinary English word inside a
    # longer description must not tag an unrelated feature page as "about".
    url = "https://postmarkapp.com/message-streams"
    text = "Learn about Message Streams and how they organize your email"
    assert classify_link(url, text) is None


def test_blog_index_is_news_not_about():
    # Plausible-style: a blog link/teaser whose surrounding text contains
    # "about" must still resolve to the blog's own category (news).
    url = "https://plausible.io/blog"
    text = "Read about our latest posts on privacy-friendly analytics"
    assert classify_link(url, text) == PageType.NEWS


def test_status_subdomain_is_not_product():
    # Plausible-style: a status-page link with vaguely product-flavored
    # surrounding prose must not be tagged "product" off a short label.
    url = "https://status.plausible.io/"
    text = "Check the current status of our platform and API uptime"
    assert classify_link(url, text) is None


# --- Strong, legitimate matches should still work --------------------------


def test_about_path_matches():
    assert classify_link("https://example.com/about", "About") == PageType.ABOUT
    assert classify_link("https://example.com/about-us", "Who we are") == PageType.ABOUT
    assert classify_link("https://example.com/company", "Company") == PageType.ABOUT


def test_product_path_matches():
    assert classify_link("https://example.com/product", "Product") == PageType.PRODUCT
    assert classify_link("https://example.com/platform", "Platform") == PageType.PRODUCT
    assert classify_link("https://example.com/solutions/enterprise", "Enterprise") == PageType.PRODUCT
    assert classify_link("https://example.com/features", "Features") == PageType.PRODUCT


def test_careers_path_matches():
    assert classify_link("https://example.com/careers", "Careers") == PageType.CAREERS
    assert classify_link("https://example.com/jobs/engineering", "Backend Engineer") == PageType.CAREERS


def test_news_path_matches():
    assert classify_link("https://example.com/blog", "Blog") == PageType.NEWS
    assert classify_link("https://example.com/changelog", "Changelog") == PageType.NEWS
    assert classify_link("https://example.com/press", "Press") == PageType.NEWS


def test_short_nav_label_fallback_when_path_is_uninformative():
    # No path signal at all (e.g. a JS-routed link) but a short, genuine
    # nav-style label should still be usable.
    assert classify_link("https://example.com/", "About") == PageType.ABOUT
    assert classify_link("https://example.com/", "Careers") == PageType.CAREERS


def test_long_prose_text_never_matches_when_path_is_uninformative():
    url = "https://example.com/"
    text = "We are hiring across the company for several exciting roles this year"
    assert classify_link(url, text) is None


# --- plan_pages integration -------------------------------------------------


def test_plan_pages_skips_unclassifiable_links_and_avoids_cross_category_hits():
    homepage_url = "https://example.com/"
    homepage_html = """
    <html><body>
      <a href="/message-streams">Learn about Message Streams and how they help</a>
      <a href="/blog">Read about our latest posts and announcements</a>
      <a href="/careers">Careers</a>
    </body></html>
    """
    plan = plan_pages(homepage_url, homepage_html, "example.com")

    assert PageType.ABOUT not in plan
    assert plan[PageType.NEWS] == "https://example.com/blog"
    assert plan[PageType.CAREERS] == "https://example.com/careers"
    assert PageType.PRODUCT not in plan
