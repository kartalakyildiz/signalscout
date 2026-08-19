"""Ties ingestion -> scraping -> AI extraction -> evidence validation ->
qualification -> database together, one company at a time. A failure in any
stage for one company degrades that company's scan (partial/failed) and
never aborts the batch."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import sessionmaker

from signalscout.ai import client as ai_client_module
from signalscout.ai import extractor
from signalscout.config import Settings
from signalscout.database import repository
from signalscout.database.models import Page
from signalscout.ingestion.csv_loader import CompanyInput
from signalscout.models.enums import Confidence, Qualification
from signalscout.models.schemas import ResearchProfile, ScrapedPage
from signalscout.scraping import scraper
from signalscout.scraping.browser_fetcher import BrowserFetcher
from signalscout.validation import evidence_validator, qualification

logger = logging.getLogger("signalscout.pipeline")


@dataclass
class CompanyRunSummary:
    company_name: str
    website: str
    status: str  # completed / partial / failed / skipped
    qualification: Qualification | None
    confidence: Confidence | None
    manual_review: bool
    skipped: bool
    error: str | None


def run_company(
    session_factory: sessionmaker,
    ai_client,
    browser_fetcher: BrowserFetcher | None,
    company_input: CompanyInput,
    settings: Settings,
    profile: ResearchProfile,
    force_rescan: bool,
) -> CompanyRunSummary:
    session = session_factory()
    try:
        company = repository.get_or_create_company(
            session, company_input.name, company_input.website, company_input.normalized_domain, company_input.target_industry
        )

        if not force_rescan and repository.has_completed_scan(session, company.id):
            logger.info("Skipping %s - already has a completed scan (use --force-rescan to redo)", company.name)
            return CompanyRunSummary(
                company_name=company.name, website=company.website, status="skipped",
                qualification=None, confidence=None, manual_review=False, skipped=True, error=None,
            )

        scan = repository.create_scan(session, company.id, ai_model=settings.openai_model)
        logger.info("Scan %d started for %s (%s)", scan.id, company.name, company.website)
        error_count = 0

        try:
            pages: list[ScrapedPage] = scraper.scan_company(company_input, settings, browser_fetcher)
        except Exception:
            logger.exception("Scraping failed for %s", company.name)
            pages = []
            error_count += 1

        saved_pages: list[tuple[ScrapedPage, Page]] = []
        for page in pages:
            db_page = repository.save_page(
                session, scan.id, page.url, page.page_type.value,
                page.fetch_method.value if page.fetch_method else None,
                page.http_status, page.title or None, page.cleaned_text or None,
                page.content_hash, page.error,
            )
            saved_pages.append((page, db_page))
            if page.error:
                error_count += 1
            logger.info(
                "  page[%s] %s -> status=%s method=%s chars=%d%s",
                page.page_type.value, page.url, page.http_status,
                page.fetch_method.value if page.fetch_method else "n/a",
                len(page.cleaned_text or ""), f" ERROR={page.error}" if page.error else "",
            )

        pages_attempted = len(pages)
        pages_succeeded = sum(1 for p in pages if p.error is None)
        filtered = [(sp, dbp) for sp, dbp in saved_pages if sp.cleaned_text and not sp.error]

        try:
            outcome, sources = extractor.extract_signals(ai_client, pages, settings, profile)
        except Exception as exc:
            logger.exception("AI extraction raised for %s", company.name)
            outcome = extractor.ExtractionOutcome(result=None, error=f"{type(exc).__name__}: {exc}")
            sources = []

        if outcome.error:
            logger.warning("AI extraction issue for %s: %s", company.name, outcome.error)
            error_count += 1
        else:
            logger.info("AI extraction returned %d raw signal(s) for %s", len(outcome.result.signals), company.name)

        page_id_by_source_id = {source.source_id: filtered[i][1].id for i, source in enumerate(sources)}
        source_map = {source.source_id: source for source in sources}

        raw_signals = outcome.result.signals if outcome.result else []
        validated = evidence_validator.validate_signals(raw_signals, source_map)
        for v in validated:
            repository.save_evidence(
                session, scan.id, page_id_by_source_id.get(v.source_id),
                v.source_id, v.signal_type.value, v.claim, v.evidence_quote,
                v.evidence_date, v.confidence.value, v.validated, v.validation_note,
            )
            logger.info(
                "  evidence[%s] %s validated=%s (%s)", v.source_id, v.signal_type.value, v.validated, v.validation_note
            )

        assessment_result = qualification.assess(validated, profile, pages_attempted, pages_succeeded, outcome.error)
        repository.save_assessment(session, scan.id, assessment_result)

        if pages_succeeded == 0:
            status = "failed"
        elif pages_succeeded < pages_attempted:
            status = "partial"
        else:
            status = "completed"

        repository.complete_scan(session, scan.id, status, pages_attempted, pages_succeeded, error_count)
        logger.info(
            "Scan %d for %s: status=%s qualification=%s manual_review=%s",
            scan.id, company.name, status, assessment_result.qualification.value, assessment_result.manual_review_required,
        )

        return CompanyRunSummary(
            company_name=company.name, website=company.website, status=status,
            qualification=assessment_result.qualification, confidence=assessment_result.confidence,
            manual_review=assessment_result.manual_review_required, skipped=False, error=None,
        )
    except Exception as exc:
        logger.exception("Unhandled error processing %s", company_input.name)
        session.rollback()
        return CompanyRunSummary(
            company_name=company_input.name, website=company_input.website, status="failed",
            qualification=None, confidence=None, manual_review=True, skipped=False, error=str(exc),
        )
    finally:
        session.close()


def run_batch(
    companies: list[CompanyInput],
    session_factory: sessionmaker,
    settings: Settings,
    profile: ResearchProfile,
    force_rescan: bool,
    use_playwright: bool,
) -> list[CompanyRunSummary]:
    ai_client = ai_client_module.build_client(settings)
    browser_fetcher = BrowserFetcher(settings) if (settings.playwright_enabled and use_playwright) else None

    summaries: list[CompanyRunSummary] = []
    try:
        for company_input in companies:
            summaries.append(
                run_company(session_factory, ai_client, browser_fetcher, company_input, settings, profile, force_rescan)
            )
    finally:
        if browser_fetcher is not None:
            browser_fetcher.close()

    return summaries
