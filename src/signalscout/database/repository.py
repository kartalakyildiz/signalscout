from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from signalscout.models.schemas import AssessmentResult
from signalscout.database.models import Assessment, Company, Evidence, Page, Scan


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_company(
    session: Session, name: str, website: str, normalized_domain: str, target_industry: str
) -> Company:
    company = session.execute(
        select(Company).where(Company.normalized_domain == normalized_domain)
    ).scalar_one_or_none()
    if company:
        return company

    company = Company(
        name=name, website=website, normalized_domain=normalized_domain, target_industry=target_industry
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def has_completed_scan(session: Session, company_id: int) -> bool:
    scan = session.execute(
        select(Scan).where(Scan.company_id == company_id, Scan.status == "completed")
    ).scalars().first()
    return scan is not None


def create_scan(session: Session, company_id: int, ai_model: str) -> Scan:
    scan = Scan(company_id=company_id, status="running", started_at=_now(), ai_model=ai_model)
    session.add(scan)
    session.commit()
    session.refresh(scan)
    return scan


def save_page(
    session: Session,
    scan_id: int,
    url: str,
    page_type: str,
    fetch_method: str | None,
    http_status: int | None,
    title: str | None,
    cleaned_text: str | None,
    content_hash: str | None,
    error: str | None,
) -> Page:
    page = Page(
        scan_id=scan_id,
        url=url,
        page_type=page_type,
        fetch_method=fetch_method,
        http_status=http_status,
        title=title,
        cleaned_text=cleaned_text,
        content_hash=content_hash,
        error=error,
    )
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


def save_evidence(
    session: Session,
    scan_id: int,
    page_id: int | None,
    source_id: str,
    signal_type: str,
    claim: str,
    evidence_quote: str,
    evidence_date: str | None,
    confidence: str,
    validated: bool,
    validation_note: str,
) -> Evidence:
    evidence = Evidence(
        scan_id=scan_id,
        page_id=page_id,
        source_id=source_id,
        signal_type=signal_type,
        claim=claim,
        evidence_quote=evidence_quote,
        evidence_date=evidence_date,
        confidence=confidence,
        validated=validated,
        validation_note=validation_note,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


def save_assessment(session: Session, scan_id: int, result: AssessmentResult) -> Assessment:
    assessment = Assessment(
        scan_id=scan_id,
        qualification=result.qualification.value,
        confidence=result.confidence.value,
        reason=result.reason,
        manual_review_required=result.manual_review_required,
        review_reason=result.review_reason,
        review_status="Pending",
    )
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


def complete_scan(
    session: Session, scan_id: int, status: str, pages_attempted: int, pages_succeeded: int, error_count: int
) -> Scan:
    scan = session.get(Scan, scan_id)
    scan.status = status
    scan.completed_at = _now()
    scan.pages_attempted = pages_attempted
    scan.pages_succeeded = pages_succeeded
    scan.error_count = error_count
    session.commit()
    session.refresh(scan)
    return scan


def update_review(session: Session, scan_id: int, review_status: str, reviewer_note: str | None) -> Assessment:
    assessment = session.execute(
        select(Assessment).where(Assessment.scan_id == scan_id)
    ).scalar_one()
    assessment.review_status = review_status
    assessment.reviewer_note = reviewer_note
    assessment.reviewed_at = _now()
    session.commit()
    session.refresh(assessment)
    return assessment


def list_latest_scans(session: Session) -> list[Scan]:
    """One scan per company - the most recently started one - eagerly loaded
    with company, pages, evidence, and assessment for export/reporting."""
    scans = session.execute(
        select(Scan)
        .options(
            selectinload(Scan.company),
            selectinload(Scan.pages),
            selectinload(Scan.evidence).selectinload(Evidence.page),
            selectinload(Scan.assessment),
        )
        .order_by(Scan.started_at.desc())
    ).scalars().all()

    latest_by_company: dict[int, Scan] = {}
    for scan in scans:
        if scan.company_id not in latest_by_company:
            latest_by_company[scan.company_id] = scan
    return list(latest_by_company.values())


def get_scan_detail(session: Session, scan_id: int) -> Scan | None:
    """A single scan, eagerly loaded with company, pages, evidence, and
    assessment - used to view any scan (not just the latest) in detail."""
    return session.execute(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(
            selectinload(Scan.company),
            selectinload(Scan.pages),
            selectinload(Scan.evidence).selectinload(Evidence.page),
            selectinload(Scan.assessment),
        )
    ).scalar_one_or_none()


def list_company_scans(session: Session, company_id: int) -> list[Scan]:
    """Lightweight scan history for one company (summary fields + assessment
    only, no pages/evidence) - newest first. Audit/history view only."""
    return session.execute(
        select(Scan)
        .where(Scan.company_id == company_id)
        .options(selectinload(Scan.assessment))
        .order_by(Scan.started_at.desc())
    ).scalars().all()
