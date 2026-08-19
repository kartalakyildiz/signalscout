from signalscout.models.enums import Confidence, Qualification, SignalType
from signalscout.models.schemas import ResearchProfile, ValidatedSignal
from signalscout.validation.qualification import assess

PROFILE = ResearchProfile(
    name="Test Profile",
    signals=[SignalType.AI_ADOPTION, SignalType.TECHNOLOGY_CHANGE, SignalType.HIRING, SignalType.EXPANSION],
    high_impact_signals=[SignalType.AI_ADOPTION, SignalType.TECHNOLOGY_CHANGE],
    min_validated_signals_high=2,
    min_validated_signals_medium=1,
)


def _signal(signal_type, confidence, validated=True, source_id="P1"):
    return ValidatedSignal(
        signal_type=signal_type,
        claim="claim",
        source_id=source_id,
        evidence_quote="quote",
        evidence_date=None,
        confidence=confidence,
        validated=validated,
        validation_note="quote found in source text" if validated else "quote not found in source text",
    )


def test_two_meaningful_validated_signals_is_high():
    signals = [
        _signal(SignalType.HIRING, Confidence.MEDIUM),
        _signal(SignalType.EXPANSION, Confidence.MEDIUM),
    ]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.HIGH
    assert result.manual_review_required is False


def test_single_high_impact_high_confidence_signal_is_high():
    signals = [_signal(SignalType.AI_ADOPTION, Confidence.HIGH)]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.HIGH
    assert result.confidence == Confidence.HIGH


def test_single_meaningful_signal_is_medium():
    signals = [_signal(SignalType.HIRING, Confidence.MEDIUM)]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.MEDIUM


def test_no_validated_signals_is_low():
    result = assess([], PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.LOW
    assert result.manual_review_required is False


def test_low_confidence_only_signal_does_not_count_as_usable():
    signals = [_signal(SignalType.HIRING, Confidence.LOW)]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.LOW


def test_invalid_evidence_only_triggers_manual_review():
    signals = [_signal(SignalType.HIRING, Confidence.MEDIUM, validated=False)]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=5, ai_error=None)
    assert result.qualification == Qualification.LOW
    assert result.manual_review_required is True


def test_ai_error_triggers_manual_review():
    result = assess([], PROFILE, pages_attempted=5, pages_succeeded=5, ai_error="API timeout")
    assert result.manual_review_required is True


def test_majority_pages_failed_sets_manual_review_true_directly():
    signals = [
        _signal(SignalType.HIRING, Confidence.MEDIUM),
        _signal(SignalType.EXPANSION, Confidence.MEDIUM),
    ]
    result = assess(signals, PROFILE, pages_attempted=5, pages_succeeded=1, ai_error=None)
    assert result.manual_review_required is True
    assert result.qualification == Qualification.HIGH  # qualification logic is independent of the review flag


def test_zero_pages_succeeded_triggers_manual_review():
    result = assess([], PROFILE, pages_attempted=5, pages_succeeded=0, ai_error=None)
    assert result.manual_review_required is True
