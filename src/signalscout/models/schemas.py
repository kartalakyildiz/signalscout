from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from signalscout.models.enums import Confidence, FetchMethod, PageType, Qualification, SignalType


class Signal(BaseModel):
    """One piece of evidence as extracted by the model. Matches the OpenAI
    structured-output schema exactly - no runtime/error state belongs here."""

    signal_type: SignalType
    claim: str
    source_id: str
    evidence_quote: str
    evidence_date: Optional[str]
    confidence: Confidence


class ExtractionResult(BaseModel):
    """The model's full structured response for one company."""

    signals: list[Signal]


class ValidatedSignal(Signal):
    validated: bool
    validation_note: str


class PageSource(BaseModel):
    """A scraped page formatted for inclusion in the LLM prompt."""

    source_id: str
    page_type: PageType
    url: str
    content: str


class CleanedPage(BaseModel):
    title: str
    text: str


class FetchResult(BaseModel):
    url: str
    status_code: Optional[int]
    html: Optional[str]
    error: Optional[str]
    fetch_method: FetchMethod


class ScrapedPage(BaseModel):
    """A single scraped, cleaned page ready for persistence and/or the LLM prompt."""

    page_type: PageType
    url: str
    fetch_method: Optional[FetchMethod]
    http_status: Optional[int]
    title: str
    cleaned_text: str
    content_hash: Optional[str]
    error: Optional[str]


class AssessmentResult(BaseModel):
    qualification: Qualification
    confidence: Confidence
    reason: str
    manual_review_required: bool
    review_reason: Optional[str]


class ResearchProfile(BaseModel):
    name: str
    signals: list[SignalType]
    high_impact_signals: list[SignalType]
    min_validated_signals_high: int
    min_validated_signals_medium: int
