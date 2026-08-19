"""SignalScout review dashboard. Reads exclusively from the SQLite database
via signalscout.database.repository - no scraping, AI, evidence-validation,
or qualification logic is duplicated here. Run with:

    streamlit run dashboard/app.py
"""
from __future__ import annotations

import html
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from signalscout.config import get_settings
from signalscout.database import repository
from signalscout.database.engine import build_session_factory
from signalscout.database.models import Scan

REVIEW_STATUS_OPTIONS = ["Pending", "Approved", "Rejected", "Needs Review"]

CUSTOM_CSS = """
<style>
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1480px; }

    /* Header */
    .ss-header { margin-bottom: 1.25rem; }
    .ss-badge {
        display: inline-block;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        line-height: 1.5;
        text-transform: uppercase;
        color: #79b8ff;
        border: 1px solid rgba(88, 166, 255, 0.35);
        background: rgba(88, 166, 255, 0.1);
        border-radius: 4px;
        padding: 0.25rem 0.6rem;
        margin-bottom: 0.6rem;
    }
    .ss-title { font-size: 1.65rem; font-weight: 650; margin: 0; line-height: 1.2; color: #f0f3f6; }
    .ss-subtitle { font-size: 0.88rem; color: #8b949e; margin: 0.2rem 0 0.55rem; }
    .ss-description {
        font-size: 0.84rem; color: #9ca3af; line-height: 1.55;
        max-width: 680px; margin: 0;
    }

    /* KPI cards */
    .ss-kpi-card {
        border: 1px solid #30363d;
        background: #161b22;
        border-radius: 8px;
        padding: 0.7rem 0.85rem;
        min-height: 4.25rem;
    }
    .ss-kpi-label {
        font-size: 0.68rem; font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.05em;
        color: #8b949e; margin-bottom: 0.3rem;
    }
    .ss-kpi-value { font-size: 1.55rem; font-weight: 600; color: #f0f3f6; line-height: 1.15; }

    /* Sidebar */
    section[data-testid="stSidebar"] { width: 268px !important; min-width: 268px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.35rem; }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 0.72rem !important; font-weight: 600 !important;
        text-transform: uppercase; letter-spacing: 0.06em;
        color: #8b949e !important; margin-bottom: 0.25rem !important;
    }
    section[data-testid="stSidebar"] hr { margin: 0.65rem 0; border-color: #21262d; }

    /* Export buttons are a secondary action, not the primary workflow */
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] { margin-top: 0.15rem; }
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button {
        width: 100%; background: transparent; border-color: #21262d;
        color: #8b949e; font-size: 0.8rem; box-shadow: none;
    }
    section[data-testid="stSidebar"] [data-testid="stDownloadButton"] button:hover {
        border-color: #58a6ff; color: #79b8ff; background: rgba(88, 166, 255, 0.06);
    }

    /* Section headings */
    .ss-section-title { font-size: 0.95rem; font-weight: 600; color: #c9d1d9; margin: 0 0 0.35rem; }
    .ss-section-hint { font-size: 0.78rem; color: #6e7681; margin: 0 0 0.75rem; }

    /* Company detail header */
    .ss-company-header { margin: 0.5rem 0 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid #21262d; }
    .ss-company-header h2 { font-size: 1.35rem; font-weight: 650; margin: 0 0 0.35rem; color: #f0f3f6; }
    .ss-company-meta { display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; margin: 0; }
    .ss-meta-sep { color: #484f58; font-size: 0.85rem; }

    /* Status pills */
    .ss-pill {
        display: inline-block; font-size: 0.75rem; font-weight: 500;
        padding: 0.15rem 0.5rem; border-radius: 4px; border: 1px solid transparent;
    }
    .ss-pill-high { background: rgba(88, 166, 255, 0.13); color: #79b8ff; border-color: rgba(88, 166, 255, 0.35); }
    .ss-pill-medium { background: rgba(210, 153, 34, 0.13); color: #e3b341; border-color: rgba(210, 153, 34, 0.35); }
    .ss-pill-low { background: #21262d; color: #8b949e; border-color: #30363d; }
    .ss-pill-approved { background: rgba(88, 166, 255, 0.13); color: #79b8ff; border-color: rgba(88, 166, 255, 0.35); }
    .ss-pill-rejected { background: rgba(248, 81, 73, 0.13); color: #ff7b72; border-color: rgba(248, 81, 73, 0.35); }
    .ss-pill-pending { background: #21262d; color: #8b949e; border-color: #30363d; }
    .ss-pill-needs-review { background: rgba(210, 153, 34, 0.13); color: #e3b341; border-color: rgba(210, 153, 34, 0.35); }

    /* Overview panel */
    .ss-panel {
        border: 1px solid #30363d; background: #161b22;
        border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;
    }
    .ss-panel-title {
        font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.05em; color: #8b949e; margin-bottom: 0.55rem;
    }
    .ss-field { margin-bottom: 0.45rem; font-size: 0.88rem; line-height: 1.45; }
    .ss-field-label { color: #8b949e; font-weight: 500; }
    .ss-field-value { color: #e6edf3; }

    /* Evidence cards */
    .ss-evidence {
        border: 1px solid #30363d; border-radius: 8px;
        padding: 0.9rem 1rem 0.85rem; margin-bottom: 0.65rem;
        background: #161b22;
    }
    .ss-evidence-valid { border-left: 3px solid #58a6ff; }
    .ss-evidence-invalid { border-left: 3px solid #f85149; }
    .ss-evidence-top {
        display: flex; justify-content: space-between; align-items: flex-start;
        gap: 0.75rem; margin-bottom: 0.45rem;
    }
    .ss-evidence-type {
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.04em; color: #8b949e;
    }
    .ss-evidence-claim { font-size: 0.92rem; font-weight: 500; color: #e6edf3; margin-bottom: 0.55rem; }
    .ss-evidence-quote {
        margin: 0 0 0.65rem; padding: 0.55rem 0.75rem;
        border-left: 2px solid #30363d; background: #0d1117;
        color: #c9d1d9; font-size: 0.86rem; line-height: 1.5; font-style: normal;
    }
    .ss-evidence-meta {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem 1rem;
    }
    .ss-meta-item { font-size: 0.8rem; line-height: 1.4; }
    .ss-meta-label {
        display: block; font-size: 0.65rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.04em; color: #6e7681;
        margin-bottom: 0.1rem;
    }
    .ss-meta-value { color: #b1bac4; word-break: break-word; }
    .ss-ev-status {
        font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.04em; padding: 0.15rem 0.45rem; border-radius: 4px; white-space: nowrap;
    }
    .ss-ev-status-valid { background: rgba(88, 166, 255, 0.13); color: #79b8ff; border: 1px solid rgba(88, 166, 255, 0.35); }
    .ss-ev-status-invalid { background: rgba(248, 81, 73, 0.13); color: #ff7b72; border: 1px solid rgba(248, 81, 73, 0.35); }
    .ss-validation-note { font-size: 0.78rem; color: #8b949e; margin-top: 0.45rem; }

    /* Tabs spacing */
    .stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.84rem; padding: 0.4rem 0.85rem; }

    hr { margin: 1rem 0; border-color: #21262d; }
</style>
"""

st.set_page_config(page_title="SignalScout", page_icon="\U0001F50E", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource
def _get_session_factory():
    settings = get_settings()
    return build_session_factory(settings)


def _format_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "—"


def _esc(value: str | None) -> str:
    return html.escape(value or "")


def _compact_website(url: str | None) -> str:
    if not url:
        return "—"
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = parsed.netloc or parsed.path.split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or url


def _pill_class(label: str | None) -> str:
    if not label:
        return ""
    return f"ss-pill ss-pill-{label.lower().replace(' ', '-')}"


def _pill(label: str | None) -> str:
    if not label:
        return "—"
    return f'<span class="{_pill_class(label)}">{_esc(label)}</span>'


def _kpi_card(label: str, value: int | str) -> str:
    return (
        f'<div class="ss-kpi-card">'
        f'<div class="ss-kpi-label">{_esc(label)}</div>'
        f'<div class="ss-kpi-value">{value}</div>'
        f"</div>"
    )


def _validated_signal_types(scan: Scan) -> list[str]:
    return sorted({e.signal_type for e in scan.evidence if e.validated})


def _last_scan_time(scan: Scan) -> datetime | None:
    return scan.completed_at or scan.started_at


def _status_cell_style(val: str, kind: str) -> str:
    palettes = {
        "qualification": {
            "High": "background-color: rgba(88, 166, 255, 0.13); color: #79b8ff;",
            "Medium": "background-color: rgba(210, 153, 34, 0.13); color: #e3b341;",
            "Low": "background-color: #21262d; color: #8b949e;",
        },
        "confidence": {
            "High": "background-color: rgba(88, 166, 255, 0.13); color: #79b8ff;",
            "Medium": "background-color: rgba(210, 153, 34, 0.13); color: #e3b341;",
            "Low": "background-color: #21262d; color: #8b949e;",
        },
        "review": {
            "Approved": "background-color: rgba(88, 166, 255, 0.13); color: #79b8ff;",
            "Rejected": "background-color: rgba(248, 81, 73, 0.13); color: #ff7b72;",
            "Pending": "background-color: #21262d; color: #8b949e;",
            "Needs Review": "background-color: rgba(210, 153, 34, 0.13); color: #e3b341;",
        },
    }
    style = palettes.get(kind, {}).get(val, "")
    if style:
        return f"{style} font-weight: 500;"
    return ""


def _style_results_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    styler = df.style
    styler = styler.map(lambda _: "font-weight: 600; color: #f0f3f6;", subset=["Company"])
    styler = styler.map(lambda _: "color: #8b949e;", subset=["Website"])
    styler = styler.map(lambda v: _status_cell_style(v, "qualification"), subset=["Qualification"])
    styler = styler.map(lambda v: _status_cell_style(v, "confidence"), subset=["Confidence"])
    styler = styler.map(lambda v: _status_cell_style(v, "review"), subset=["Review Status"])
    return styler


def _get_selected_index(filtered_len: int) -> int:
    if filtered_len == 0:
        return 0
    state = st.session_state.get("results_table")
    if state and state.get("selection", {}).get("rows"):
        idx = state["selection"]["rows"][0]
        if 0 <= idx < filtered_len:
            return idx
    return 0


def _render_evidence_card(evidence) -> str:
    valid = evidence.validated
    card_class = "ss-evidence ss-evidence-valid" if valid else "ss-evidence ss-evidence-invalid"
    status_class = "ss-ev-status-valid" if valid else "ss-ev-status-invalid"
    status_label = "Validated" if valid else "Invalid"
    source_url = evidence.page.url if evidence.page else "—"
    page_type = evidence.page.page_type if evidence.page else "—"
    note_html = ""
    if not valid and evidence.validation_note:
        note_html = f'<div class="ss-validation-note">Validation note: {_esc(evidence.validation_note)}</div>'
    return f"""
    <div class="{card_class}">
        <div class="ss-evidence-top">
            <span class="ss-evidence-type">{_esc(evidence.signal_type)}</span>
            <span class="ss-ev-status {status_class}">{status_label}</span>
        </div>
        <div class="ss-evidence-claim">{_esc(evidence.claim)}</div>
        <blockquote class="ss-evidence-quote">{_esc(evidence.evidence_quote)}</blockquote>
        <div class="ss-evidence-meta">
            <div class="ss-meta-item">
                <span class="ss-meta-label">Source</span>
                <span class="ss-meta-value">{_esc(source_url)}</span>
            </div>
            <div class="ss-meta-item">
                <span class="ss-meta-label">Page Type</span>
                <span class="ss-meta-value">{_esc(page_type)}</span>
            </div>
            <div class="ss-meta-item">
                <span class="ss-meta-label">Confidence</span>
                <span class="ss-meta-value">{_esc(evidence.confidence)}</span>
            </div>
        </div>
        {note_html}
    </div>
    """


def _overview_panel(title: str, fields: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div class="ss-field"><span class="ss-field-label">{_esc(label)}:</span> '
        f'<span class="ss-field-value">{value}</span></div>'
        for label, value in fields
    )
    return f'<div class="ss-panel"><div class="ss-panel-title">{_esc(title)}</div>{rows}</div>'


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="ss-header">
        <span class="ss-badge">Evidence-First Research Pipeline</span>
        <h1 class="ss-title">SignalScout</h1>
        <p class="ss-subtitle">AI-Powered Web Research &amp; Qualification</p>
        <p class="ss-description">
            Combines public-web research, structured AI extraction, evidence verification,
            deterministic qualification, and manual review into one auditable pipeline.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
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

kpi_items = [
    ("Companies Scanned", total_companies),
    ("High Priority", high_count),
    ("Medium Priority", medium_count),
    ("Low / Reject", low_count),
    ("Manual Review", manual_review_count),
]
kpi_cols = st.columns(5)
for col, (label, value) in zip(kpi_cols, kpi_items):
    col.markdown(_kpi_card(label, value), unsafe_allow_html=True)

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
    st.header("Export")
    csv_path = settings.exports_dir / "signalscout_results.csv"
    xlsx_path = settings.exports_dir / "signalscout_results.xlsx"
    if csv_path.exists():
        st.download_button("Download CSV", data=csv_path.read_bytes(), file_name=csv_path.name, mime="text/csv")
    else:
        st.caption("CSV export not generated yet.")
    if xlsx_path.exists():
        st.download_button(
            "Download XLSX",
            data=xlsx_path.read_bytes(),
            file_name=xlsx_path.name,
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

st.markdown(
    f'<p class="ss-section-title">Results ({len(filtered_scans)} of {total_companies})</p>'
    '<p class="ss-section-hint">Select a row to view company details below.</p>',
    unsafe_allow_html=True,
)

if not filtered_scans:
    st.info("No companies match the current filters.")
    st.stop()

table_rows = []
for scan in filtered_scans:
    assessment = scan.assessment
    validated_types = _validated_signal_types(scan)
    table_rows.append({
        "Company": scan.company.name,
        "Website": _compact_website(scan.company.website),
        "Industry": scan.company.target_industry or "—",
        "Signals": ", ".join(validated_types) if validated_types else "—",
        "Qualification": assessment.qualification if assessment else "—",
        "Confidence": assessment.confidence if assessment else "—",
        "Evidence": sum(1 for e in scan.evidence if e.validated),
        "Review Status": assessment.review_status if assessment else "—",
    })

results_df = pd.DataFrame(table_rows)
styled_df = _style_results_table(results_df)
st.dataframe(
    styled_df,
    width="stretch",
    hide_index=True,
    key="results_table",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Company": st.column_config.TextColumn("Company", width=140),
        "Website": st.column_config.TextColumn("Website", width=100),
        "Industry": st.column_config.TextColumn("Industry", width=110),
        "Signals": st.column_config.TextColumn("Signals", width=260),
        "Qualification": st.column_config.TextColumn("Qualification", width=100),
        "Confidence": st.column_config.TextColumn("Confidence", width=100),
        "Evidence": st.column_config.NumberColumn("Evidence", width=80),
        "Review Status": st.column_config.TextColumn("Review Status", width=115),
    },
)

# ---------------------------------------------------------------------------
# Company detail view
# ---------------------------------------------------------------------------

selected_idx = _get_selected_index(len(filtered_scans))
selected_scan = filtered_scans[selected_idx]
assessment = selected_scan.assessment

qual_label = assessment.qualification if assessment else None
conf_label = assessment.confidence if assessment else None
st.markdown(
    f'<div class="ss-company-header">'
    f"<h2>{_esc(selected_scan.company.name)}</h2>"
    f'<div class="ss-company-meta">{_pill(qual_label)}'
    f'<span class="ss-meta-sep">·</span>{_pill(conf_label)}</div>'
    f"</div>",
    unsafe_allow_html=True,
)

tab_overview, tab_signals, tab_evidence, tab_pages, tab_review, tab_history = st.tabs(
    ["Overview", "Detected Signals", "Evidence", "Pages Inspected", "Manual Review", "Scan History"]
)

# --- Overview ---
with tab_overview:
    left, right = st.columns(2)
    with left:
        st.markdown(
            _overview_panel("Company Profile", [
                ("Company", _esc(selected_scan.company.name)),
                ("Website", _esc(selected_scan.company.website)),
                ("Target Industry", _esc(selected_scan.company.target_industry or "—")),
            ]),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            _overview_panel("Assessment", [
                ("Qualification", _pill(qual_label)),
                ("Confidence", _pill(conf_label)),
                ("Last Scan", _esc(_format_dt(_last_scan_time(selected_scan)))),
                ("Scan Status", _esc(selected_scan.status)),
            ]),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ss-panel-title" style="margin-top:0.25rem">Why Qualified</div>', unsafe_allow_html=True)
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
        st.dataframe(
            signals_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Signal Type": st.column_config.TextColumn("Signal Type", width="small"),
                "Confidence": st.column_config.TextColumn("Confidence", width="small"),
                "Validated": st.column_config.TextColumn("Validated", width="small"),
                "Claim": st.column_config.TextColumn("Claim", width="large"),
            },
        )
    else:
        st.write("No signals were extracted for this scan.")

# --- Evidence ---
with tab_evidence:
    if not selected_scan.evidence:
        st.write("No evidence recorded for this scan.")
    else:
        for evidence in selected_scan.evidence:
            st.markdown(_render_evidence_card(evidence), unsafe_allow_html=True)

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
            pages_df,
            width="stretch",
            hide_index=True,
            column_config={"URL": st.column_config.LinkColumn("URL")},
        )
    else:
        st.write("No pages recorded for this scan.")

# --- Manual Review ---
with tab_review:
    if assessment is None:
        st.write("No assessment recorded for this scan - nothing to review.")
    else:
        review_cols = st.columns(2)
        with review_cols[0]:
            st.markdown("**Current status**")
            st.markdown(_pill(assessment.review_status), unsafe_allow_html=True)
        with review_cols[1]:
            if assessment.reviewed_at:
                st.caption(f"Last reviewed: {_format_dt(assessment.reviewed_at)}")
        if assessment.reviewer_note:
            st.markdown("**Current note**")
            st.write(assessment.reviewer_note)

        with st.form(key=f"review_form_{selected_scan.id}"):
            new_status = st.selectbox(
                "Review status",
                REVIEW_STATUS_OPTIONS,
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
