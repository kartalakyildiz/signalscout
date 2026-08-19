"""Reads and validates the input companies CSV: normalizes URLs and
deduplicates by normalized domain. Malformed rows are reported, never raised."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from signalscout.ingestion.normalizer import normalize_url, normalized_domain

REQUIRED_COLUMNS = ["Company", "Website", "Target Industry"]


@dataclass
class CompanyInput:
    name: str
    website: str
    raw_website: str
    normalized_domain: str
    target_industry: str


def load_companies(csv_path: str | Path) -> dict:
    path = Path(csv_path)
    valid: list[CompanyInput] = []
    invalid: list[dict] = []
    duplicates: list[dict] = []
    seen_domains: dict[str, int] = {}

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing_columns:
            raise ValueError(f"input CSV is missing required columns: {missing_columns}")

        for line_no, row in enumerate(reader, start=2):  # header is line 1
            name = (row.get("Company") or "").strip()
            raw_website = (row.get("Website") or "").strip()
            target_industry = (row.get("Target Industry") or "").strip()

            if not name:
                invalid.append({"row": line_no, "company": name, "raw_website": raw_website, "reason": "missing company name"})
                continue

            normalized = normalize_url(raw_website)
            if not normalized:
                invalid.append({"row": line_no, "company": name, "raw_website": raw_website, "reason": "empty or unusable URL"})
                continue

            domain = normalized_domain(normalized)
            if not domain:
                invalid.append({"row": line_no, "company": name, "raw_website": raw_website, "reason": "could not extract a domain"})
                continue

            if domain in seen_domains:
                duplicates.append({
                    "row": line_no, "company": name, "website": normalized,
                    "normalized_domain": domain, "duplicate_of_row": seen_domains[domain],
                })
                continue

            seen_domains[domain] = line_no
            valid.append(CompanyInput(
                name=name, website=normalized, raw_website=raw_website,
                normalized_domain=domain, target_industry=target_industry,
            ))

    return {
        "companies": valid,
        "invalid": invalid,
        "duplicates": duplicates,
        "summary": {
            "total_rows": len(valid) + len(invalid) + len(duplicates),
            "valid": len(valid),
            "invalid": len(invalid),
            "duplicates": len(duplicates),
        },
    }
