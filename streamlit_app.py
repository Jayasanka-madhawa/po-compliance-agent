"""PO Compliance Agent — Streamlit UI.

Local:  API_URL=http://localhost:8000 streamlit run streamlit_app.py
Docker: docker compose up -d streamlit  → http://localhost:8502
"""
from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 120.0

SAMPLE_FILES = [
    ("po_clean_ceylon_industrial.pdf", "Auto Accept"),
    ("po_messy_serendib_parts.pdf", "Human Review"),
    ("po_partial_lakpura.csv", "Human Review"),
]


def api_url() -> str:
    return st.session_state.get("api_url", DEFAULT_API_URL).rstrip("/")


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


def refresh_health() -> None:
    health, error = api_get("/health")
    st.session_state["health_cache"] = {"health": health, "error": error}


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


def show_decision(decision: str | None) -> None:
    label = (decision or "UNKNOWN").replace("_", " ").title()
    if decision == "AUTO_ACCEPT":
        st.success(f"**{label}**")
    elif decision == "MANUALLY_APPROVED":
        st.success(f"**Manually Approved**")
    elif decision == "HUMAN_REVIEW":
        st.warning(f"**{label}**")
    elif decision in {"REJECTED", "PROCESSING_FAILED"}:
        st.error(f"**{label}**")
    else:
        st.info(f"**{label}**")


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
    show_decision(job.get("decision"))

    if job.get("error"):
        st.error(job["error"])
    elif job.get("explanation"):
        st.info(job["explanation"])

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
        st.markdown("**Why flagged**")
        for reason in reasons:
            st.markdown(f"- {reason}")

    rag = job.get("rag_validation") or {}
    if rag:
        checks = [
            ("Vendor", (rag.get("vendor_check") or {}).get("status")),
            ("Payment terms", (rag.get("payment_terms_check") or {}).get("status")),
            ("Spending", (rag.get("spending_check") or {}).get("status")),
        ]
        check_cols = st.columns(len(checks))
        for col, (name, status) in zip(check_cols, checks):
            col.metric(name, (status or "—").replace("_", " ").title())

        math_ok = (rag.get("math_validation") or {}).get("total_reconciled")
        st.write(f"Math reconciled: **{'Yes' if math_ok else 'No'}**")

    line_items = extraction.get("line_items") or []
    if line_items:
        st.markdown("**Line items**")
        st.dataframe(pd.DataFrame(line_items), use_container_width=True, hide_index=True)

    with st.expander("Full API response"):
        st.json(job)


@st.fragment
def page_process_order() -> None:
    st.caption("Upload a PO file for extraction, policy checks, and routing.")

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
        st.divider()
        show_job_details(result)


def page_review_queue() -> None:
    st.caption("Approve or reject orders flagged for human review.")

    top_left, top_right = st.columns([3, 1])
    with top_left:
        reviewer = st.text_input(
            "Reviewer email",
            value=st.session_state.get("reviewer", "procurement.manager@company.com"),
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

    st.divider()
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
    st.caption("Recent processed purchase orders.")

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

    st.divider()
    show_job_details(job)


PAGES = {
    "Process Order": page_process_order,
    "Review Queue": page_review_queue,
    "Job History": page_job_history,
}


def render_sidebar() -> None:
    with st.sidebar:
        st.title("PO Compliance")
        st.caption("Purchase order validation")
        st.divider()

        st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
            key="nav_page",
        )

        st.divider()
        st.text_input("API URL", key="api_url")

        if st.button("Check API", use_container_width=True):
            refresh_health()

        cache = st.session_state.get("health_cache")
        if cache:
            health, error = cache["health"], cache["error"]
            if error:
                st.error("API offline")
                st.caption(error)
            elif isinstance(health, dict):
                status = health.get("status", "unknown")
                if status == "ok":
                    st.success("API connected")
                else:
                    st.warning(f"API status: {status}")
                st.caption(
                    f"Postgres: {health.get('postgres', '—')} · "
                    f"Qdrant: {health.get('qdrant', '—')}"
                )
        else:
            st.caption("Click **Check API** to test connection.")


def main() -> None:
    st.set_page_config(
        page_title="PO Compliance Agent",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "api_url" not in st.session_state:
        st.session_state["api_url"] = DEFAULT_API_URL
    if "reviewer" not in st.session_state:
        st.session_state["reviewer"] = "procurement.manager@company.com"
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "Process Order"
    if "health_cache" not in st.session_state:
        refresh_health()

    current_url = api_url()
    if st.session_state.get("_last_api_url") != current_url:
        st.session_state["_last_api_url"] = current_url
        invalidate_list_caches()
        st.session_state.pop("health_cache", None)
        refresh_health()

    prefetch_data()
    render_sidebar()

    page = st.session_state["nav_page"]
    st.title(page)
    PAGES[page]()


if __name__ == "__main__":
    main()
