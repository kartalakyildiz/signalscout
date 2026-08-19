"""Prompt construction and evidence-first source formatting. The model only
ever sees the [SOURCE:Pn] blocks built here - it is never told anything else
about the company."""
from __future__ import annotations

from signalscout.config import Settings
from signalscout.models.schemas import PageSource, ResearchProfile, ScrapedPage

SYSTEM_PROMPT = """You are a research analyst extracting business buying-signal evidence for B2B prospecting.

Rules you must follow exactly:
- Only use the supplied SOURCE blocks in the user message. Do not use any outside knowledge about this company.
- Never invent, assume, or infer facts that are not directly stated in the supplied content.
- Every signal you report must reference a real source_id from the supplied sources (e.g. "P1").
- evidence_quote must be a short excerpt copied verbatim (word-for-word) from that source's CONTENT - not paraphrased or summarized.
- Prefer concrete, factual statements (e.g. "opened a new office in Austin", "hiring a Head of AI") over vague marketing language ("industry-leading", "world-class", "innovative").
- Marketing language alone is not strong evidence - do not report a signal based only on adjectives with no concrete fact behind them.
- Read claims for their actual meaning, not just keyword presence. For example, a careers page stating there are NO open positions is evidence AGAINST active hiring, not a "Hiring" signal - only report "Hiring" when the source shows an actual open role, active recruiting, or explicit hiring intent.
- Use confidence "Low" for vague or marketing-flavored claims, "Medium" for plausible but indirect evidence, "High" only for explicit, unambiguous statements.
- evidence_date should be a date or time reference mentioned in the source text if present, otherwise null - never guess a date.
- If a source does not contain clear evidence for any signal type, do not report anything from it.
- If no supported signals are found across all sources, return an empty signals list.
- Do not explain your reasoning or add commentary - return only the structured result.
"""


def build_page_sources(pages: list[ScrapedPage], settings: Settings) -> list[PageSource]:
    """Assigns source ids (P1, P2, ...) to successfully-scraped pages only,
    truncating per-page and total content to the configured budgets."""
    sources: list[PageSource] = []
    used = 0
    for page in pages:
        if not page.cleaned_text or page.error:
            continue
        if used >= settings.total_prompt_char_budget:
            break

        content = page.cleaned_text[: settings.page_content_char_limit]
        remaining_budget = settings.total_prompt_char_budget - used
        content = content[:remaining_budget]
        if not content:
            break
        used += len(content)

        sources.append(
            PageSource(source_id=f"P{len(sources) + 1}", page_type=page.page_type, url=page.url, content=content)
        )
    return sources


def format_sources_block(sources: list[PageSource]) -> str:
    blocks = []
    for source in sources:
        blocks.append(
            f"[SOURCE:{source.source_id}]\n"
            f"TYPE: {source.page_type.value}\n"
            f"URL: {source.url}\n"
            f"CONTENT:\n{source.content}\n"
        )
    return "\n".join(blocks)


def build_user_prompt(sources: list[PageSource], profile: ResearchProfile) -> str:
    signal_names = ", ".join(s.value for s in profile.signals)
    return (
        f"Look for evidence of these signal types only: {signal_names}.\n\n"
        f"{format_sources_block(sources)}"
    )
