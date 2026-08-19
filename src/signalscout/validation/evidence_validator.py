"""Evidence validation: every signal's evidence_quote must actually appear in
the scraped source text it claims to come from. Conservative normalized
substring matching - the LLM is never trusted as the source of truth."""
from __future__ import annotations

import re

from signalscout.models.schemas import PageSource, Signal, ValidatedSignal

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def validate_evidence_quote(quote: str, source_text: str) -> tuple[bool, str]:
    if not quote or not quote.strip():
        return False, "empty evidence quote"
    if not source_text:
        return False, "source text unavailable"
    if normalize(quote) in normalize(source_text):
        return True, "quote found in source text"
    return False, "quote not found in source text (normalized substring match failed)"


def validate_signals(signals: list[Signal], source_map: dict[str, PageSource]) -> list[ValidatedSignal]:
    """source_map must be the exact source_id -> PageSource mapping that was
    sent to the model for this scan, so an unresolvable source_id is always
    treated as invalid rather than guessed at."""
    validated: list[ValidatedSignal] = []
    for signal in signals:
        source = source_map.get(signal.source_id)
        if source is None:
            ok, note = False, "Unknown source_id"
        else:
            ok, note = validate_evidence_quote(signal.evidence_quote, source.content)
        validated.append(ValidatedSignal(**signal.model_dump(), validated=ok, validation_note=note))
    return validated
