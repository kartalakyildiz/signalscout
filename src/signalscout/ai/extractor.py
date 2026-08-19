"""Calls the OpenAI Responses API with Pydantic structured outputs and
returns an ExtractionOutcome - runtime/API failure is represented here, kept
separate from ExtractionResult (which mirrors the model's schema exactly)."""
from __future__ import annotations

import logging

from openai import OpenAI
from pydantic import BaseModel

from signalscout.ai import prompts
from signalscout.config import Settings
from signalscout.models.schemas import ExtractionResult, PageSource, ResearchProfile, ScrapedPage

logger = logging.getLogger("signalscout.ai.extractor")


class ExtractionOutcome(BaseModel):
    result: ExtractionResult | None
    error: str | None


def extract_signals(
    client: OpenAI, pages: list[ScrapedPage], settings: Settings, profile: ResearchProfile
) -> tuple[ExtractionOutcome, list[PageSource]]:
    sources = prompts.build_page_sources(pages, settings)
    if not sources:
        return ExtractionOutcome(result=ExtractionResult(signals=[]), error="no usable scraped content to analyze"), sources

    user_prompt = prompts.build_user_prompt(sources, profile)

    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            text_format=ExtractionResult,
        )
    except Exception as exc:  # openai.* API errors, network errors, etc.
        logger.warning("OpenAI extraction call failed: %s", exc)
        return ExtractionOutcome(result=None, error=f"{type(exc).__name__}: {exc}"), sources

    parsed = response.output_parsed
    if parsed is None:
        return ExtractionOutcome(result=None, error="model did not return parsed structured output"), sources

    return ExtractionOutcome(result=parsed, error=None), sources
