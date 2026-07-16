"""PO Compliance Agent — Streamlit UI.

Local:  API_URL=http://localhost:8000 streamlit run streamlit_app.py
Docker: docker compose up -d streamlit  → http://localhost:8502
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_REVIEWER = "pocompliance.demo@gmail.com"
REQUEST_TIMEOUT = 120.0
KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent / "knowledge_base"

OFFICE_CSS = """
<style>
    .stApp {
        background-color: #dde4ee;
        font-size: 0.98rem;
    }
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1120px;
        font-size: 0.98rem;
    }
    [data-testid="stSidebar"] {
        background-color: #e8edf5;
        border-right: 1px solid #c5d0de;
        font-size: 0.95rem;
    }
    [data-testid="stSidebar"] .stMarkdown h1 {
        font-size: 1.08rem;
        font-weight: 600;
        color: #0f172a;
        letter-spacing: -0.01em;
    }
    [data-testid="stSidebar"] .stCaption {
        color: #475569;
        font-size: 0.86rem;
    }
    [data-testid="stSidebar"] label {
        font-size: 0.95rem !important;
    }
    .sidebar-brand {
        margin: 0 0 0.15rem 0;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.25;
        letter-spacing: -0.02em;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        margin-bottom: 0.5rem;
    }
    [data-testid="stCaptionContainer"] {
        font-size: 0.86rem;
    }
    [data-testid="stAlert"] {
        font-size: 0.95rem;
        padding: 0.5rem 0.75rem;
    }
    [data-testid="stAlert"] p {
        font-size: 0.95rem;
        margin: 0;
    }
    [data-testid="stExpander"] summary {
        font-size: 0.95rem;
    }
    [data-testid="stDataFrame"] {
        font-size: 0.9rem;
    }
    [data-testid="stTable"] {
        font-size: 0.86rem;
    }
    [data-testid="stTable"] table {
        font-size: 0.86rem;
    }
    .ag-theme-streamlit {
        font-size: 0.9rem !important;
    }
    div[data-testid="stMetric"] label {
        font-size: 0.83rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.08rem;
    }
    .page-header {
        margin: 0 0 1.35rem 0;
    }
    .page-header h1 {
        margin: 0;
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a;
        letter-spacing: -0.025em;
        line-height: 1.15;
    }
    .page-header p {
        margin: 0.35rem 0 0.85rem 0;
        color: #64748b;
        font-size: 0.92rem;
        line-height: 1.45;
        max-width: 42rem;
    }
    .page-header-rule {
        height: 2px;
        width: 3.5rem;
        background: #1e40af;
        border-radius: 1px;
    }
    .block-container h3 {
        font-size: 1.02rem;
        font-weight: 600;
        margin-top: 0.75rem;
    }
    .block-container p, .block-container li {
        font-size: 0.95rem;
        line-height: 1.45;
    }
    [data-testid="stForm"] {
        padding: 0.25rem 0;
    }
    .stButton > button {
        font-size: 0.95rem;
    }
    .stButton > button[kind="primary"] {
        background-color: #1e40af;
        border-color: #1e40af;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #1e3a8a;
        border-color: #1e3a8a;
    }
    .policy-heading {
        font-size: 0.96rem;
        font-weight: 600;
        color: #0f172a;
        border-bottom: 1px solid #c5d0de;
        padding-bottom: 0.25rem;
        margin: 1.1rem 0 0.35rem 0;
    }
    .policy-heading:first-of-type {
        margin-top: 0;
    }
    .policy-caption {
        font-size: 0.8rem;
        color: #64748b;
        margin: 0 0 0.45rem 0;
        line-height: 1.35;
    }
    .policy-body {
        font-size: 0.86rem;
        line-height: 1.4;
        color: #334155;
    }
    .policy-body ul {
        margin: 0.2rem 0 0.55rem 0;
        padding-left: 1.1rem;
    }
    .policy-body li {
        font-size: 0.86rem;
        margin-bottom: 0.12rem;
    }
    .policy-body p {
        font-size: 0.86rem;
        margin: 0.2rem 0 0.35rem 0;
    }
    .policy-subhead {
        font-size: 0.88rem;
        font-weight: 600;
        color: #1e293b;
        margin: 0.45rem 0 0.15rem 0;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid #b8c5d4 !important;
        border-radius: 8px;
        padding: 1rem 1.25rem 1.1rem;
        margin: 0.75rem 0 1rem 0;
    }
    .job-detail-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.85rem;
    }
    .job-badge {
        display: inline-block;
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.28rem 0.65rem;
        border-radius: 999px;
        letter-spacing: 0.01em;
    }
    .job-badge-auto_accept,
    .job-badge-manually_approved {
        color: #166534;
        background: #dcfce7;
        border: 1px solid #bbf7d0;
    }
    .job-badge-human_review {
        color: #92400e;
        background: #fef3c7;
        border: 1px solid #fde68a;
    }
    .job-badge-rejected,
    .job-badge-processing_failed {
        color: #991b1b;
        background: #fee2e2;
        border: 1px solid #fecaca;
    }
    .job-badge-unknown {
        color: #334155;
        background: #e2e8f0;
        border: 1px solid #cbd5e1;
    }
    .job-detail-id {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
        white-space: nowrap;
    }
    .job-detail-label {
        font-size: 0.9rem;
        font-weight: 600;
        color: #1e293b;
        margin: 0.85rem 0 0.35rem 0;
    }
</style>
"""


def inject_office_theme() -> None:
    st.markdown(OFFICE_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="page-header">'
        f"<h1>{title}</h1>"
        f"<p>{subtitle}</p>"
        f'<div class="page-header-rule"></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

SAMPLE_FILES = [
    ("po_clean_ceylon_industrial.pdf", "Auto Accept"),
    ("po_messy_serendib_parts.pdf", "Human Review"),
    ("po_partial_lakpura.csv", "Human Review"),
]


def api_url() -> str:
    return DEFAULT_API_URL.rstrip("/")


@st.cache_resource
def _http_client(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=30.0)


def _client() -> httpx.Client:
    return _http_client(api_url())


def api_get(path: str, **params: object) -> tuple[object | None, str | None]:
    try:
        response = _client().get(path, params=params or None)
        response.raise_for_status()
        return response.json(), None
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        return None, f"{exc.response.status_code}: {detail}"
    except httpx.HTTPError as exc:
        return None, str(exc)


def api_post_file(
    path: str,
    file_bytes: bytes,
    filename: str,
    data: dict[str, str],
) -> tuple[dict | None, str | None]:
    try:
        with httpx.Client(base_url=api_url(), timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                path,
                files={"file": (filename, file_bytes)},
                data=data,
            )
            response.raise_for_status()
            return response.json(), None
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        return None, f"{exc.response.status_code}: {detail}"
    except httpx.HTTPError as exc:
        return None, str(exc)


def api_patch_json(path: str, payload: dict) -> tuple[dict | None, str | None]:
    try:
        response = _client().patch(path, json=payload)
        response.raise_for_status()
        return response.json(), None
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or str(exc)
        return None, f"{exc.response.status_code}: {detail}"
    except httpx.HTTPError as exc:
        return None, str(exc)


def invalidate_list_caches() -> None:
    st.session_state.pop("review_jobs", None)
    st.session_state.pop("history_jobs", None)
    st.session_state.pop("review_jobs_table", None)
    st.session_state.pop("history_jobs_table", None)
    st.session_state.pop("review_selected_job_id", None)
    st.session_state.pop("history_selected_job_id", None)


def load_review_jobs(force: bool = False) -> tuple[list[dict], str | None]:
    if not force and "review_jobs" in st.session_state:
        return st.session_state["review_jobs"], None

    jobs, error = api_get("/review-queue", limit=50)
    if error:
        return [], error

    jobs = jobs or []
    st.session_state["review_jobs"] = jobs
    return jobs, None


def load_history_jobs(limit: int, force: bool = False) -> tuple[list[dict], str | None]:
    cached = st.session_state.get("history_jobs")
    if not force and cached and cached.get("limit") == limit:
        return cached["jobs"], None

    jobs, error = api_get("/jobs", limit=limit)
    if error:
        return [], error

    jobs = jobs or []
    st.session_state["history_jobs"] = {"limit": limit, "jobs": jobs}
    return jobs, error


def _read_policy_file(filename: str) -> str:
    path = KNOWLEDGE_BASE_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _policy_heading(title: str, caption: str | None = None) -> None:
    cap = f'<div class="policy-caption">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="policy-heading">{title}</div>{cap}',
        unsafe_allow_html=True,
    )


def _compact_policy_html(text: str) -> str:
    parts: list[str] = ['<div class="policy-body">']
    in_ul = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue
        if stripped.startswith("## "):
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f'<p class="policy-subhead">{stripped[3:]}</p>')
        elif stripped.startswith("- "):
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            parts.append(f"<p>{stripped}</p>")
    if in_ul:
        parts.append("</ul>")
    parts.append("</div>")
    return "\n".join(parts)


def _policy_list_html(items: list[str]) -> str:
    rows = "".join(f"<li>{item}</li>" for item in items)
    return f'<div class="policy-body"><ul>{rows}</ul></div>'


def page_policies() -> None:
    vendor_path = KNOWLEDGE_BASE_DIR / "approved_vendors.csv"
    _policy_heading(
        "Approved vendors",
        "Only approved vendors are eligible for automatic acceptance.",
    )
    if vendor_path.exists():
        vendors = pd.read_csv(vendor_path)
        st.table(vendors)
    else:
        st.markdown(
            _policy_list_html(
                [
                    "<strong>Ceylon Industrial Bearings (Pvt) Ltd</strong> (VND-001)",
                    "<strong>Lakpura Logistics (Pvt) Ltd</strong> (VND-002)",
                ]
            ),
            unsafe_allow_html=True,
        )

    payment_policy = _read_policy_file("payment_policy.md")
    _policy_heading("Payment terms")
    if payment_policy:
        st.markdown(_compact_policy_html(payment_policy), unsafe_allow_html=True)
    else:
        st.markdown(
            _policy_list_html(
                [
                    "Auto-approve: Net 15, Net 30, Due on Receipt (max <strong>30 days</strong>)",
                    "Human review: Net 45, 60, 90 or any terms above 30 days",
                ]
            ),
            unsafe_allow_html=True,
        )

    approval_policy = _read_policy_file("approval_policy.md")
    _policy_heading("Spending limits")
    if approval_policy:
        st.markdown(_compact_policy_html(approval_policy), unsafe_allow_html=True)
    else:
        st.markdown(
            _policy_list_html(
                [
                    "Auto-approve: up to <strong>LKR 1,000,000</strong>",
                    "Manager review: LKR 1,000,001 – 5,000,000",
                    "Director review: above LKR 5,000,000",
                ]
            ),
            unsafe_allow_html=True,
        )

    _policy_heading("Routing rules")
    st.markdown(
        _policy_list_html(
            [
                "<strong>Auto Accept</strong> — all policy checks pass, extraction confidence ≥ 75%",
                "<strong>Human Review</strong> — vendor, payment terms, spending limit, missing fields, or math mismatch",
                "<strong>Manually Approved</strong> — reviewer approved a flagged PO in the review queue",
                "<strong>Rejected</strong> — reviewer rejected a flagged PO",
            ]
        ),
        unsafe_allow_html=True,
    )


def prefetch_data() -> None:
    """Load list data once so tab switches stay instant."""
    if "review_jobs" not in st.session_state:
        load_review_jobs()
    if "history_jobs" not in st.session_state:
        load_history_jobs(limit=20)


def format_money(amount: float | None) -> str:
    if amount is None:
        return "—"
    return f"LKR {amount:,.0f}"


def format_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0%}"


def _decision_label(decision: str | None) -> str:
    if decision == "MANUALLY_APPROVED":
        return "Manually Approved"
    return (decision or "UNKNOWN").replace("_", " ").title()


def _decision_badge_class(decision: str | None) -> str:
    key = (decision or "unknown").lower()
    if key not in {
        "auto_accept",
        "manually_approved",
        "human_review",
        "rejected",
        "processing_failed",
    }:
        return "job-badge-unknown"
    return f"job-badge-{key}"


def _detail_label(title: str) -> None:
    st.markdown(f'<p class="job-detail-label">{title}</p>', unsafe_allow_html=True)


def _render_job_detail_header(job: dict) -> None:
    decision = job.get("decision")
    job_id = (job.get("job_id") or "")[:8] or "—"
    badge_class = _decision_badge_class(decision)
    label = _decision_label(decision)
    st.markdown(
        f'<div class="job-detail-header">'
        f'<span class="job-badge {badge_class}">{label}</span>'
        f'<span class="job-detail-id">Job #{job_id}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def jobs_table_df(jobs: list[dict]) -> pd.DataFrame:
    rows = []
    for job in jobs:
        extraction = job.get("extraction") or {}
        job_id = job.get("job_id") or ""
        rows.append(
            {
                "_job_id": job_id,
                "Job ID": job_id[:8] if job_id else "—",
                "Decision": job.get("decision") or "—",
                "Vendor": extraction.get("vendor_name") or "—",
                "PO #": extraction.get("po_number") or "—",
                "Total": format_money(extraction.get("total_amount")),
                "Confidence": format_pct(job.get("confidence")),
            }
        )
    return pd.DataFrame(rows)


def _find_job_by_id(jobs: list[dict], job_id: str | None) -> dict | None:
    if not job_id:
        return None
    for job in jobs:
        if job.get("job_id") == job_id:
            return job
    return None


def _aggrid_selected_rows(response: dict) -> list[dict]:
    selected = response.get("selected_rows")
    if selected is None:
        return []
    if isinstance(selected, pd.DataFrame):
        if selected.empty:
            return []
        return selected.to_dict("records")
    if isinstance(selected, list):
        return selected
    return []


def render_selectable_jobs_table(
    jobs: list[dict],
    *,
    table_key: str,
    selected_job_key: str,
    hint: str = "Click any row in the table to view that PO below.",
) -> dict | None:
    st.caption(hint)

    df = jobs_table_df(jobs)
    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_column("_job_id", hide=True)
    builder.configure_selection("single", use_checkbox=False)
    builder.configure_grid_options(
        suppressRowClickSelection=False,
        rowSelection="single",
    )

    selected_id = st.session_state.get(selected_job_key)
    pre_selected: list[int] = []
    if selected_id:
        matches = df.index[df["_job_id"] == selected_id].tolist()
        if matches:
            pre_selected = matches
    elif jobs:
        pre_selected = [0]
        st.session_state[selected_job_key] = jobs[0].get("job_id")

    response = AgGrid(
        df,
        gridOptions=builder.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        theme="streamlit",
        key=table_key,
        fit_columns_on_grid_load=True,
        pre_selected_rows=pre_selected,
        use_container_width=True,
        height=min(48 + len(jobs) * 42, 420),
    )

    selected_rows = _aggrid_selected_rows(response)
    if selected_rows:
        st.session_state[selected_job_key] = selected_rows[0].get("_job_id")

    job = _find_job_by_id(jobs, st.session_state.get(selected_job_key))
    if job is None and jobs:
        st.session_state[selected_job_key] = jobs[0].get("job_id")
        job = jobs[0]
    return job


def show_job_details(job: dict) -> None:
    with st.container(border=True):
        _render_job_detail_header(job)

        if job.get("error"):
            st.error(job["error"])
        elif job.get("explanation"):
            st.caption(job["explanation"])

        extraction = job.get("extraction") or {}
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vendor", extraction.get("vendor_name") or "—")
        c2.metric("PO number", extraction.get("po_number") or "—")
        c3.metric("Total", format_money(extraction.get("total_amount")))
        c4.metric("Confidence", format_pct(job.get("confidence")))

        if extraction.get("fields_missing"):
            st.warning("Missing: " + ", ".join(extraction["fields_missing"]))
        if extraction.get("ambiguities"):
            st.warning("Ambiguities: " + ", ".join(extraction["ambiguities"]))

        reasons = job.get("reasons") or []
        if reasons:
            _detail_label("Why flagged")
            for reason in reasons:
                st.markdown(f"- {reason}")

        rag = job.get("rag_validation") or {}
        if rag:
            _detail_label("Policy checks")
            checks = [
                ("Vendor", (rag.get("vendor_check") or {}).get("status")),
                ("Payment terms", (rag.get("payment_terms_check") or {}).get("status")),
                ("Spending", (rag.get("spending_check") or {}).get("status")),
            ]
            check_cols = st.columns(len(checks))
            for col, (name, status) in zip(check_cols, checks):
                col.metric(name, (status or "—").replace("_", " ").title())

            math_ok = (rag.get("math_validation") or {}).get("total_reconciled")
            st.caption(f"Math reconciled: **{'Yes' if math_ok else 'No'}**")

        line_items = extraction.get("line_items") or []
        if line_items:
            _detail_label("Line items")
            st.dataframe(pd.DataFrame(line_items), use_container_width=True, hide_index=True)

        with st.expander("Full API response"):
            st.json(job)


@st.fragment
def page_process_order() -> None:
    with st.form("process_form", clear_on_submit=False):
        uploaded = st.file_uploader(
            "Attachment (PDF, CSV, or image)",
            type=["pdf", "csv", "png", "jpg", "jpeg", "webp"],
        )
        sender = st.text_input("Sender email", value="vendor@test.com")
        subject = st.text_input("Subject", value="Purchase Order Submission")
        submitted = st.form_submit_button("Process", type="primary", use_container_width=True)

    st.caption(
        "Sample files in `sample_documents/`: "
        + " · ".join(f"{name} → {decision}" for name, decision in SAMPLE_FILES)
    )

    if submitted:
        if uploaded is None:
            st.error("Please choose a file first.")
            return

        with st.spinner("Processing… this may take 15–30 seconds."):
            data: dict[str, str] = {}
            if sender.strip():
                data["sender"] = sender.strip()
            if subject.strip():
                data["subject"] = subject.strip()

            result, error = api_post_file(
                "/process-order",
                uploaded.getvalue(),
                uploaded.name,
                data,
            )

        if error:
            st.error(f"Request failed: {error}")
            return

        st.session_state["last_result"] = result
        invalidate_list_caches()
        st.success("Processing complete.")

    result = st.session_state.get("last_result")
    if result:
        show_job_details(result)


def page_review_queue() -> None:
    top_left, top_right = st.columns([3, 1])
    with top_left:
        reviewer = st.text_input(
            "Reviewer email",
            value=st.session_state.get("reviewer", DEFAULT_REVIEWER),
            key="reviewer_email",
        )
        st.session_state["reviewer"] = reviewer
    with top_right:
        st.write("")
        if st.button("Refresh", key="refresh_review", use_container_width=True):
            st.session_state.pop("review_jobs_table", None)
            st.session_state.pop("review_selected_job_id", None)
            load_review_jobs(force=True)

    jobs, error = load_review_jobs()
    if error:
        st.error(f"Could not load review queue: {error}")
        return

    if not jobs:
        st.success("No orders waiting for review.")
        return

    st.metric("Pending", len(jobs))
    job = render_selectable_jobs_table(
        jobs,
        table_key="review_jobs_table",
        selected_job_key="review_selected_job_id",
        hint="Click any row in the table to view and review that order.",
    )
    if job is None:
        return

    show_job_details(job)

    with st.form(f"review_{job.get('job_id')}"):
        note = st.text_area("Review note (optional)")
        c1, c2 = st.columns(2)
        approve = c1.form_submit_button("Approve", type="primary", use_container_width=True)
        reject = c2.form_submit_button("Reject", use_container_width=True)

        if approve or reject:
            if not reviewer.strip():
                st.error("Reviewer email is required.")
            else:
                action = "approve" if approve else "reject"
                updated, review_error = api_patch_json(
                    f"/jobs/{job['job_id']}/review",
                    {
                        "action": action,
                        "reviewer": reviewer.strip(),
                        "note": note.strip() or None,
                    },
                )
                if review_error:
                    st.error(f"Review failed: {review_error}")
                else:
                    st.session_state.pop("last_result", None)
                    invalidate_list_caches()
                    st.success(f"Saved. New decision: {updated.get('decision')}")


def page_job_history() -> None:
    top_left, top_right = st.columns([3, 1])
    with top_left:
        limit = st.selectbox("Show latest", [10, 20, 50], index=1, key="history_limit")
    with top_right:
        st.write("")
        if st.button("Refresh", key="refresh_history", use_container_width=True):
            st.session_state.pop("history_jobs_table", None)
            st.session_state.pop("history_selected_job_id", None)
            load_history_jobs(limit=limit, force=True)

    jobs, error = load_history_jobs(limit=limit)
    if error:
        st.error(f"Could not load jobs: {error}")
        return

    if not jobs:
        st.info("No jobs yet. Process a purchase order first.")
        return

    job = render_selectable_jobs_table(
        jobs,
        table_key="history_jobs_table",
        selected_job_key="history_selected_job_id",
        hint="Click any row in the table to view that job's PO details.",
    )
    if job is None:
        return

    show_job_details(job)


PAGES = {
    "Review Queue": page_review_queue,
    "Job History": page_job_history,
    "Process Order": page_process_order,
    "Policies": page_policies,
}


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<p class="sidebar-brand">Procurement Compliance</p>', unsafe_allow_html=True)
        st.caption("Purchase order intake & validation")
        st.divider()

        st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
            key="nav_page",
        )


PAGE_SUBTITLES = {
    "Process Order": "Upload vendor purchase orders for extraction and policy checks.",
    "Review Queue": "Review flagged orders and record approval decisions.",
    "Job History": "Audit trail of processed purchase orders.",
    "Policies": "Corporate procurement policies used for automated validation.",
}


def main() -> None:
    st.set_page_config(
        page_title="Procurement Compliance",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_office_theme()

    if "reviewer" not in st.session_state or st.session_state.get("reviewer") == (
        "procurement.manager@company.com"
    ):
        st.session_state["reviewer"] = DEFAULT_REVIEWER
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Review Queue"

    prefetch_data()
    render_sidebar()

    page = st.session_state["nav_page"]
    render_page_header(page, PAGE_SUBTITLES.get(page, ""))
    PAGES[page]()


if __name__ == "__main__":
    main()
