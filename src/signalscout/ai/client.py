"""All OpenAI-specific construction lives here - the rest of the codebase
only ever imports ExtractionOutcome/ExtractionResult, never the OpenAI SDK."""
from __future__ import annotations

from openai import OpenAI

from signalscout.config import Settings


def build_client(settings: Settings) -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set (check your .env file)")
    return OpenAI(api_key=settings.openai_api_key)
