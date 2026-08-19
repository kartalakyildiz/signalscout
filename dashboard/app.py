"""SignalScout review dashboard. Reads exclusively from the SQLite database
via signalscout.database.repository - no scraping, AI, evidence-validation,
or qualification logic is duplicated here. Run with:

    streamlit run dashboard/app.py
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from signalscout.config import get_settings
from signalscout.database import repository
from signalscout.database.engine import build_session_factory
from signalscout.database.models import Scan

QUALIFICATION_COLORS = {"High": "green", "Medium": "orange", "Low": "gray"}
CONFIDENCE_COLORS = {"High": "green", "Medium": "orange", "Low": "gray"}
REVIEW_STATUS_OPTIONS = ["Pending", "Approved", "Rejected", "Needs Review"]

st.set_page_config(page_title="SignalScout", page_icon="\U0001F50E", layout="wide")


@st.cache_resource
def _get_session_factory():
    settings = get_settings()
    return build_session_factory(settings)


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "—"


def _badge(label: str | None, colors: dict) -> str:
    if not label:
        return "—"
    color = colors.get(label, "gray")
    return f":{color}[**{label}**]"


def _validated_signal_types(scan: Scan) -> list[str]:
    return sorted({e.signal_type for e in scan.evidence if e.validated})


def _last_scan_time(scan: Scan) -> datetime | None:
    return scan.completed_at or scan.started_at


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("SignalScout")
st.caption("AI-Powered Web Research & Qualification")
st.write(
    "Combines public-web research, structured AI extraction, evidence verification, "
    "deterministic qualification, and manual review into one auditable pipeline."
)

settings = get_settings()
session_factory = _get_session_factory()
session = session_factory()

latest_scans = repository.list_latest_scans(session)

if not latest_scans:
    st.info(
        "No scans found yet. Run the pipeline first:\n\n"
        "`python -m signalscout run --input data/sample_companies.csv`"
    )
    st.stop()

# ---------------------------------------------------------------------------
# KPIs (latest scan per company only - historical rescans are not double-counted)
# ---------------------------------------------------------------------------

total_companies = len(latest_scans)
high_count = sum(1 for s in latest_scans if s.assessment and s.assessment.qualification == "High")
medium_count = sum(1 for s in latest_scans if s.assessment and s.assessment.qualification == "Medium")
low_count = sum(1 for s in latest_scans if s.assessment and s.assessment.qualification == "Low")
manual_review_count = sum(1 for s in latest_scans if s.assessment and s.assessment.manual_review_required)

kpi_cols = st.columns(5)
kpi_cols[0].metric("Companies Scanned", total_companies)
kpi_cols[1].metric("High Priority", high_count)
kpi_cols[2].metric("Medium Priority", medium_count)
kpi_cols[3].metric("Low / Reject", low_count)
kpi_cols[4].metric("Manual Review", manual_review_count)

st.divider()

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Filters")

    sel_qualification = st.multiselect("Qualification", ["High", "Medium", "Low"])
    sel_confidence = st.multiselect("Confidence", ["High", "Medium", "Low"])

    all_signal_types = sorted({sig for s in latest_scans for sig in _validated_signal_types(s)})
    sel_signal_types = st.multiselect("Signal Type", all_signal_types)

    all_review_statuses = sorted({s.assessment.review_status for s in latest_scans if s.assessment})
    sel_review_status = st.multiselect("Review Status", all_review_statuses or REVIEW_STATUS_OPTIONS)

    manual_only = st.toggle("Manual review only")

    st.divider()
    st.header("Exports")
    csv_path = settings.exports_dir / "signalscout_results.csv"
    xlsx_path = settings.exports_dir / "signalscout_results.xlsx"
    if csv_path.exists():
        st.download_button("Download CSV", data=csv_path.read_bytes(), file_name=csv_path.name, mime="text/csv")
    else:
        st.caption("CSV export not generated yet.")
    if xlsx_path.exists():
        st.download_button(
            "Download XLSX", data=xlsx_path.read_bytes(), file_name=xlsx_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.caption("XLSX export not generated yet.")


def _matches_filters(scan: Scan) -> bool:
    assessment = scan.assessment
    if sel_qualification and (not assessment or assessment.qualification not in sel_qualification):
        return False
    if sel_confidence and (not assessment or assessment.confidence not in sel_confidence):
        return False
    if sel_review_status and (not assessment or assessment.review_status not in sel_review_status):
        return False
    if manual_only and not (assessment and assessment.manual_review_required):
        return False
    if sel_signal_types:
        if not set(_validated_signal_types(scan)).intersection(sel_signal_types):
            return False
    return True


filtered_scans = [s for s in latest_scans if _matches_filters(s)]

# ---------------------------------------------------------------------------
# Main results table
# ---------------------------------------------------------------------------

st.subheader(f"Results ({len(filtered_scans)} of {total_companies})")

if not filtered_scans:
    st.info("No companies match the current filters.")
    st.stop()

table_rows = []
for scan in filtered_scans:
    assessment = scan.assessment
    validated_types = _validated_signal_types(scan)
    table_rows.append({
        "Company": scan.company.name,
        "Website": scan.company.website,
        "Target Industry": scan.company.target_industry or "—",
        "Signals": ", ".join(validated_types) if validated_types else "—",
        "Qualification": assessment.qualification if assessment else "—",
        "Confidence": assessment.confidence if assessment else "—",
        "Validated Evidence": sum(1 for e in scan.evidence if e.validated),
        "Review Status": assessment.review_status if assessment else "—",
        "Last Scan": _format_dt(_last_scan_time(scan)),
    })

results_df = pd.DataFrame(table_rows)
st.dataframe(
    results_df,
    width="stretch",
    hide_index=True,
    column_config={"Website": st.column_config.LinkColumn("Website")},
)

# ---------------------------------------------------------------------------
# Company detail view
# ---------------------------------------------------------------------------

st.divider()
company_names = [scan.company.name for scan in filtered_scans]
selected_name = st.selectbox("Select a company to view details", company_names)
selected_scan = next(s for s in filtered_scans if s.company.name == selected_name)

st.header(selected_scan.company.name)

tab_overview, tab_signals, tab_evidence, tab_pages, tab_review, tab_history = st.tabs(
    ["Overview", "Detected Signals", "Evidence", "Pages Inspected", "Manual Review", "Scan History"]
)

assessment = selected_scan.assessment

# --- Overview ---
with tab_overview:
    left, right = st.columns(2)
    with left:
        st.write("**Company:**", selected_scan.company.name)
        st.write("**Website:**", selected_scan.company.website)
        st.write("**Target Industry:**", selected_scan.company.target_industry or "—")
    with right:
        st.write("**Qualification:**", _badge(assessment.qualification if assessment else None, QUALIFICATION_COLORS))
        st.write("**Confidence:**", _badge(assessment.confidence if assessment else None, CONFIDENCE_COLORS))
        st.write("**Last Scan:**", _format_dt(_last_scan_time(selected_scan)))
        st.write("**Scan Status:**", selected_scan.status)

    st.subheader("Why Qualified")
    if assessment:
        st.info(assessment.reason)
        if assessment.manual_review_required:
            st.warning(f"Flagged for manual review: {assessment.review_reason or 'see evidence for details'}")
    else:
        st.write("No assessment recorded for this scan.")

# --- Detected Signals ---
with tab_signals:
    if selected_scan.evidence:
        signals_df = pd.DataFrame([{
            "Signal Type": e.signal_type,
            "Confidence": e.confidence,
            "Validated": "Yes" if e.validated else "No",
            "Claim": e.claim,
        } for e in selected_scan.evidence])
        st.dataframe(signals_df, width="stretch", hide_index=True)
    else:
        st.write("No signals were extracted for this scan.")

# --- Evidence ---
with tab_evidence:
    if not selected_scan.evidence:
        st.write("No evidence recorded for this scan.")
    for e in selected_scan.evidence:
        with st.container(border=True):
            header_col, status_col = st.columns([4, 1])
            header_col.markdown(f"**{e.signal_type}** — {e.claim}")
            status_col.markdown(":green[Validated]" if e.validated else ":red[Invalid]")

            st.markdown(f"> {e.evidence_quote}")

            meta_cols = st.columns(3)
            meta_cols[0].write(f"**Source:** {e.page.url if e.page else '—'}")
            meta_cols[1].write(f"**Page type:** {e.page.page_type if e.page else '—'}")
            meta_cols[2].write(f"**Confidence:** {e.confidence}")

            if not e.validated:
                st.caption(f"Validation note: {e.validation_note}")

# --- Pages Inspected ---
with tab_pages:
    if selected_scan.pages:
        pages_df = pd.DataFrame([{
            "Page Type": p.page_type,
            "URL": p.url,
            "Fetch Method": p.fetch_method or "—",
            "HTTP Status": p.http_status if p.http_status is not None else "—",
            "Result": "Success" if p.error is None else f"Error: {p.error}",
            "Fetched At": _format_dt(p.fetched_at),
        } for p in selected_scan.pages])
        st.dataframe(
            pages_df, width="stretch", hide_index=True,
            column_config={"URL": st.column_config.LinkColumn("URL")},
        )
    else:
        st.write("No pages recorded for this scan.")

# --- Manual Review ---
with tab_review:
    if assessment is None:
        st.write("No assessment recorded for this scan - nothing to review.")
    else:
        st.write("**Current status:**", assessment.review_status)
        if assessment.reviewer_note:
            st.write("**Current note:**", assessment.reviewer_note)
        if assessment.reviewed_at:
            st.caption(f"Last reviewed: {_format_dt(assessment.reviewed_at)}")

        with st.form(key=f"review_form_{selected_scan.id}"):
            new_status = st.selectbox(
                "Review status", REVIEW_STATUS_OPTIONS,
                index=REVIEW_STATUS_OPTIONS.index(assessment.review_status)
                if assessment.review_status in REVIEW_STATUS_OPTIONS else 0,
            )
            new_note = st.text_area("Reviewer note", value=assessment.reviewer_note or "")
            submitted = st.form_submit_button("Save")
            if submitted:
                repository.update_review(session, selected_scan.id, new_status, new_note or None)
                st.success("Review saved.")
                st.rerun()

# --- Scan History ---
with tab_history:
    history = repository.list_company_scans(session, selected_scan.company_id)
    if history:
        history_df = pd.DataFrame([{
            "Scan Started": _format_dt(h.started_at),
            "Status": h.status,
            "Qualification": h.assessment.qualification if h.assessment else "—",
            "Confidence": h.assessment.confidence if h.assessment else "—",
            "Pages Succeeded / Attempted": f"{h.pages_succeeded}/{h.pages_attempted}",
        } for h in history])
        st.dataframe(history_df, width="stretch", hide_index=True)
    else:
        st.write("No scan history available.")
