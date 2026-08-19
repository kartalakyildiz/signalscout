"""CSV + XLSX export, reading only from the database (no business logic
lives here - qualification/validation are already decided by the time a
Scan reaches this module)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from signalscout.config import Settings
from signalscout.database import repository
from signalscout.database.models import Scan


def _company_row(scan: Scan) -> dict:
    company = scan.company
    assessment = scan.assessment
    validated_evidence = [e for e in scan.evidence if e.validated]
    signal_types = sorted({e.signal_type for e in validated_evidence})
    evidence_texts = [f'[{e.signal_type}] {e.claim} ("{e.evidence_quote}")' for e in validated_evidence]
    source_urls = sorted({e.page.url for e in validated_evidence if e.page})
    last_checked = scan.completed_at or scan.started_at

    return {
        "Company": company.name,
        "Website": company.website,
        "Target Industry": company.target_industry,
        "Signal Types": ", ".join(signal_types),
        "Qualification": assessment.qualification if assessment else "",
        "Confidence": assessment.confidence if assessment else "",
        "Reason": assessment.reason if assessment else "",
        "Validated Evidence Count": len(validated_evidence),
        "Manual Review": "Yes" if (assessment and assessment.manual_review_required) else "No",
        "Evidence": " | ".join(evidence_texts),
        "Source URLs": ", ".join(source_urls),
        "Last Checked": last_checked.isoformat(timespec="seconds") if last_checked else "",
    }


def _evidence_rows(scans: list[Scan]) -> list[dict]:
    rows = []
    for scan in scans:
        for e in scan.evidence:
            rows.append({
                "Company": scan.company.name,
                "Signal Type": e.signal_type,
                "Claim": e.claim,
                "Evidence Quote": e.evidence_quote,
                "Source URL": e.page.url if e.page else "",
                "Confidence": e.confidence,
                "Validated": e.validated,
                "Validation Note": e.validation_note,
            })
    return rows


def _scan_summary_rows(scans: list[Scan]) -> list[dict]:
    rows = []
    for scan in scans:
        rows.append({
            "Company": scan.company.name,
            "Status": scan.status,
            "Pages Attempted": scan.pages_attempted,
            "Pages Succeeded": scan.pages_succeeded,
            "Error Count": scan.error_count,
            "AI Model": scan.ai_model,
            "Started At": scan.started_at.isoformat(timespec="seconds") if scan.started_at else "",
            "Completed At": scan.completed_at.isoformat(timespec="seconds") if scan.completed_at else "",
        })
    return rows


def _autofit_columns(xlsx_path: Path, max_width: int = 60) -> None:
    workbook = load_workbook(xlsx_path)
    for sheet in workbook.worksheets:
        for column_cells in sheet.columns:
            length = max((len(str(cell.value)) if cell.value is not None else 0) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), max_width)
    workbook.save(xlsx_path)


def generate_exports(session: Session, settings: Settings) -> dict:
    scans = repository.list_latest_scans(session)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)

    company_rows = [_company_row(s) for s in scans]
    evidence_rows = _evidence_rows(scans)
    summary_rows = _scan_summary_rows(scans)

    csv_path = settings.exports_dir / "signalscout_results.csv"
    xlsx_path = settings.exports_dir / "signalscout_results.xlsx"

    pd.DataFrame(company_rows).to_csv(csv_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame(company_rows).to_excel(writer, sheet_name="Companies", index=False)
        pd.DataFrame(evidence_rows).to_excel(writer, sheet_name="Evidence", index=False)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Scan Summary", index=False)

    _autofit_columns(xlsx_path)

    return {"csv_path": csv_path, "xlsx_path": xlsx_path, "total_rows": len(company_rows)}
