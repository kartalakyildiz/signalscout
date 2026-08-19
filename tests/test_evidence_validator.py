from signalscout.models.enums import Confidence, PageType, SignalType
from signalscout.models.schemas import PageSource, Signal
from signalscout.validation.evidence_validator import validate_evidence_quote, validate_signals

SOURCE_TEXT = "Acme Corp is hiring a Head of AI to lead our new machine learning platform."


def _signal(source_id="P1", evidence_quote="Acme Corp is hiring a Head of AI", evidence_date=None):
    return Signal(
        signal_type=SignalType.AI_ADOPTION,
        claim="Company is hiring for AI leadership",
        source_id=source_id,
        evidence_quote=evidence_quote,
        evidence_date=evidence_date,
        confidence=Confidence.HIGH,
    )


def test_validate_evidence_quote_exact_match_accepted():
    ok, note = validate_evidence_quote("Acme Corp is hiring a Head of AI", SOURCE_TEXT)
    assert ok is True
    assert "found" in note


def test_validate_evidence_quote_whitespace_and_case_variance_still_accepted():
    ok, _ = validate_evidence_quote("  ACME corp is   hiring a head of ai  ", SOURCE_TEXT)
    assert ok is True


def test_validate_evidence_quote_fabricated_text_rejected():
    ok, note = validate_evidence_quote("Acme Corp acquired a competitor last week", SOURCE_TEXT)
    assert ok is False
    assert "not found" in note


def test_validate_evidence_quote_empty_rejected():
    ok, note = validate_evidence_quote("", SOURCE_TEXT)
    assert ok is False
    assert "empty" in note


def test_validate_signals_unknown_source_id_rejected():
    source_map = {"P1": PageSource(source_id="P1", page_type=PageType.HOMEPAGE, url="https://acme.test", content=SOURCE_TEXT)}
    signals = [_signal(source_id="P99")]
    validated = validate_signals(signals, source_map)
    assert len(validated) == 1
    assert validated[0].validated is False
    assert validated[0].validation_note == "Unknown source_id"


def test_validate_signals_real_and_fabricated_mixed():
    source_map = {"P1": PageSource(source_id="P1", page_type=PageType.HOMEPAGE, url="https://acme.test", content=SOURCE_TEXT)}
    signals = [
        _signal(source_id="P1", evidence_quote="Acme Corp is hiring a Head of AI"),
        _signal(source_id="P1", evidence_quote="Acme Corp is opening a Mars office"),
    ]
    validated = validate_signals(signals, source_map)
    assert validated[0].validated is True
    assert validated[1].validated is False
