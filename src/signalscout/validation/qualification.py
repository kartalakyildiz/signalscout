"""Deterministic qualification: the LLM extracts and classifies evidence,
but Python business logic - using only validated evidence - decides the
final qualification, assessment confidence, and manual-review flag. Pure
function, no I/O, so every branch is directly unit-testable."""
from __future__ import annotations

from signalscout.models.enums import Confidence, Qualification
from signalscout.models.schemas import AssessmentResult, ResearchProfile, ValidatedSignal


def _assessment_confidence(qualification: Qualification, usable: list[ValidatedSignal], high_impact_hit: bool) -> Confidence:
    if qualification == Qualification.HIGH:
        if high_impact_hit or any(e.confidence == Confidence.HIGH for e in usable):
            return Confidence.HIGH
        return Confidence.MEDIUM
    if qualification == Qualification.MEDIUM:
        if any(e.confidence in (Confidence.HIGH, Confidence.MEDIUM) for e in usable):
            return Confidence.MEDIUM
        return Confidence.LOW
    return Confidence.LOW


def _build_reason(usable: list[ValidatedSignal], qualification: Qualification, high_impact_hit: bool) -> str:
    if not usable:
        return "No validated evidence of target signals was found on the scraped pages."
    signal_names = ", ".join(sorted({e.signal_type.value for e in usable}))
    if qualification == Qualification.HIGH and high_impact_hit:
        return f"High-confidence validated evidence of a high-impact signal: {signal_names}."
    return f"{len(usable)} validated signal(s) found: {signal_names}."


def assess(
    validated_evidence: list[ValidatedSignal],
    profile: ResearchProfile,
    pages_attempted: int,
    pages_succeeded: int,
    ai_error: str | None,
) -> AssessmentResult:
    usable = [e for e in validated_evidence if e.validated and e.confidence != Confidence.LOW]
    high_impact_hit = any(
        e.validated and e.signal_type in profile.high_impact_signals and e.confidence == Confidence.HIGH
        for e in validated_evidence
    )

    manual_review_required = False
    review_reasons: list[str] = []

    if ai_error:
        manual_review_required = True
        review_reasons.append("AI extraction failed or returned incomplete data")

    if pages_attempted > 0 and pages_succeeded == 0:
        manual_review_required = True
        review_reasons.append("no pages could be scraped")
    elif pages_attempted > 0 and pages_succeeded < pages_attempted / 2:
        manual_review_required = True
        review_reasons.append("majority of attempted pages failed to scrape")

    invalid_count = sum(1 for e in validated_evidence if not e.validated)
    if invalid_count and not usable:
        manual_review_required = True
        review_reasons.append("evidence failed validation")

    if len(usable) >= profile.min_validated_signals_high or high_impact_hit:
        qualification = Qualification.HIGH
    elif len(usable) >= profile.min_validated_signals_medium:
        qualification = Qualification.MEDIUM
    else:
        qualification = Qualification.LOW

    confidence = _assessment_confidence(qualification, usable, high_impact_hit)
    reason = _build_reason(usable, qualification, high_impact_hit)

    return AssessmentResult(
        qualification=qualification,
        confidence=confidence,
        reason=reason,
        manual_review_required=manual_review_required,
        review_reason="; ".join(review_reasons) if review_reasons else None,
    )
