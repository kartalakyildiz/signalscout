from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from signalscout.config import get_settings, load_research_profile
from signalscout.database.engine import build_session_factory
from signalscout.export.exporter import generate_exports
from signalscout.ingestion.csv_loader import load_companies
from signalscout.logging_setup import configure_logging
from signalscout.models.enums import Qualification
from signalscout.pipeline.runner import run_batch

app = typer.Typer(add_completion=False)


@app.callback()
def main() -> None:
    """SignalScout - AI-powered web research and qualification system."""


@app.command("run")
def run(
    input: str = typer.Option("data/sample_companies.csv", "--input", help="Path to the companies CSV."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Only process the first N companies."),
    playwright: bool = typer.Option(True, "--playwright/--no-playwright", help="Enable/disable the Playwright fallback."),
    force_rescan: bool = typer.Option(False, "--force-rescan", help="Rescan companies even if a completed scan already exists."),
) -> None:
    settings = get_settings()
    configure_logging(settings.logs_dir)
    logger = logging.getLogger("signalscout.cli")

    profile = load_research_profile()

    loaded = load_companies(input)
    companies = loaded["companies"]
    summary = loaded["summary"]

    typer.echo(
        f"Loaded {summary['valid']} valid compan{'y' if summary['valid'] == 1 else 'ies'}, "
        f"{summary['invalid']} invalid, {summary['duplicates']} duplicate(s) from {input}."
    )
    for item in loaded["invalid"]:
        typer.echo(f"  INVALID   row {item['row']}: {item['company']!r} ({item['raw_website']!r}) - {item['reason']}")
    for item in loaded["duplicates"]:
        typer.echo(
            f"  DUPLICATE row {item['row']}: {item['company']!r} ({item['website']}) "
            f"duplicates domain of row {item['duplicate_of_row']}"
        )

    if limit is not None:
        companies = companies[:limit]

    if not companies:
        typer.echo("No valid companies to process. Exiting.")
        raise typer.Exit(code=1)

    logger.info("Starting batch run: %d companies, playwright=%s, force_rescan=%s", len(companies), playwright, force_rescan)
    session_factory = build_session_factory(settings)

    summaries = run_batch(companies, session_factory, settings, profile, force_rescan, playwright)

    with session_factory() as session:
        export_paths = generate_exports(session, settings)

    processed = [s for s in summaries if not s.skipped]
    skipped_count = len(summaries) - len(processed)
    high = sum(1 for s in processed if s.qualification == Qualification.HIGH)
    medium = sum(1 for s in processed if s.qualification == Qualification.MEDIUM)
    low = sum(1 for s in processed if s.qualification == Qualification.LOW)
    manual_review = sum(1 for s in processed if s.manual_review)

    db_path = settings.database_url.replace("sqlite:///", "")

    typer.echo("")
    typer.echo("SignalScout Scan Complete")
    typer.echo("")
    typer.echo(f"Companies processed: {len(processed)}")
    if skipped_count:
        typer.echo(f"Skipped (already scanned): {skipped_count}")
    typer.echo(f"High priority: {high}")
    typer.echo(f"Medium priority: {medium}")
    typer.echo(f"Low / Reject: {low}")
    typer.echo(f"Manual review: {manual_review}")
    typer.echo("")
    typer.echo("Database:")
    typer.echo(f"  {db_path}")
    typer.echo("")
    typer.echo("Exports:")
    typer.echo(f"  {export_paths['xlsx_path']}")
    typer.echo(f"  {export_paths['csv_path']}")

    logger.info("Batch run complete: %d processed, %d high, %d medium, %d low, %d manual review", len(processed), high, medium, low, manual_review)
