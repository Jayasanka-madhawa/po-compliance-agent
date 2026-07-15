"""PO Compliance Agent — Streamlit dashboard.

Run locally:
  API_URL=http://localhost:8000 streamlit run streamlit_app.py

Docker:
  docker compose up -d streamlit  → http://localhost:8502
"""
from __future__ import annotations

import os

import httpx
import streamlit as st

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")
PROCESS_TIMEOUT = 120.0

DECISION_LABELS = {
    "AUTO_ACCEPT": "✅ Auto Accept",
    "HUMAN_REVIEW": "👤 Human Review",
    "REJECTED": "❌ Rejected",
    "PROCESSING_FAILED": "⚠️ Processing Failed",
    "PENDING_ROUTING": "⏳ Pending",
}


def api_url() -> str:
    return st.session_state.get("api_url", DEFAULT_API_URL).rstrip("/")


def get_client() -> httpx.Client:
    return httpx.Client(base_url=api_url(), timeout=PROCESS_TIMEOUT)


def check_health() -> dict | None:
    try:
        with get_client() as client:
            response = client.get("/health", timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        st.sidebar.error(f"API unreachable: {exc}")
        return None


def process_order(
    file_bytes: bytes,
    filename: str,
    sender: str | None,
    subject: str | None,
) -> dict:
    files = {"file": (filename, file_bytes)}
    data: dict[str, str] = {}
    if sender:
        data["sender"] = sender
    if subject:
        data["subject"] = subject

    with get_client() as client:
        response = client.post("/process-order", files=files, data=data)
        response.raise_for_status()
        return response.json()


def fetch_review_queue() -> list[dict]:
    with get_client() as client:
        response = client.get("/review-queue", params={"limit": 50})
        response.raise_for_status()
        return response.json()


def fetch_jobs(limit: int = 20) -> list[dict]:
    with get_client() as client:
        response = client.get("/jobs", params={"limit": limit})
        response.raise_for_status()
        return response.json()


def submit_review(job_id: str, action: str, reviewer: str, note: str | None) -> dict:
    payload = {"action": action, "reviewer": reviewer, "note": note or None}
    with get_client() as client:
        response = client.patch(f"/jobs/{job_id}/review", json=payload)
        response.raise_for_status()
        return response.json()


def render_decision_banner(result: dict) -> None:
    decision = result.get("decision", "")
    label = DECISION_LABELS.get(decision, decision)
    if decision == "AUTO_ACCEPT":
        st.success(label)
    elif decision == "HUMAN_REVIEW":
        st.warning(label)
    elif decision in {"REJECTED", "PROCESSING_FAILED"}:
        st.error(label)
    else:
        st.info(label)


def render_extraction(extraction: dict | None) -> None:
    if not extraction:
        return
    cols = st.columns(3)
    cols[0].metric("Vendor", extraction.get("vendor_name", "—"))
    cols[1].metric("PO Number", extraction.get("po_number") or "—")
    cols[2].metric(
        "Total",
        f"LKR {extraction.get('total_amount', 0):,.0f}",
    )
    st.caption(
        f"Terms: {extraction.get('payment_terms') or '—'} "
        f"({extraction.get('payment_terms_days') or '—'} days) · "
        f"Confidence: {extraction.get('extraction_confidence', 0):.0%}"
    )
    if extraction.get("line_items"):
        st.dataframe(extraction["line_items"], use_container_width=True)


def render_rag_validation(rag: dict | None) -> None:
    if not rag:
        return
    if rag.get("issues"):
        st.markdown("**RAG issues:** " + ", ".join(f"`{i}`" for i in rag["issues"]))
    else:
        st.markdown("**RAG:** no issues")

    vendor = rag.get("vendor_check") or {}
    payment = rag.get("payment_terms_check") or {}
    spending = rag.get("spending_check") or {}
    math_check = rag.get("math_validation") or {}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vendor", vendor.get("status", "—"))
    c2.metric("Payment", payment.get("status", "—"))
    c3.metric("Spending", spending.get("status", "—"))
    reconciled = math_check.get("total_reconciled")
    c4.metric("Math OK", "Yes" if reconciled else "No")


def page_process_po() -> None:
    st.header("Process Purchase Order")
    st.caption("Upload a PDF or CSV purchase order for extraction, RAG validation, and routing.")

    uploaded = st.file_uploader(
        "PO attachment",
        type=["pdf", "csv", "png", "jpg", "jpeg", "webp"],
    )
    col1, col2 = st.columns(2)
    sender = col1.text_input("Sender email (optional)", value="vendor@test.com")
    subject = col2.text_input("Email subject (optional)", value="Purchase Order Submission")

    if st.button("Process order", type="primary", disabled=uploaded is None):
        assert uploaded is not None
        with st.spinner("Processing… extraction and RAG can take 15–30 seconds."):
            try:
                result = process_order(
                    uploaded.getvalue(),
                    uploaded.name,
                    sender or None,
                    subject or None,
                )
                st.session_state["last_result"] = result
            except httpx.HTTPError as exc:
                st.error(f"Request failed: {exc}")
                return

    result = st.session_state.get("last_result")
    if not result:
        return

    st.divider()
    render_decision_banner(result)

    cols = st.columns(3)
    cols[0].metric("Job ID", result.get("job_id", "—")[:8] + "…")
    cols[1].metric("Confidence", f"{result.get('confidence', 0):.0%}")
    cols[2].metric("Status", result.get("status", "—"))

    if result.get("reasons"):
        st.markdown("**Reasons for review**")
        for reason in result["reasons"]:
            st.markdown(f"- {reason}")

    if result.get("explanation"):
        st.info(result["explanation"])

    if result.get("error"):
        st.error(result["error"])

    with st.expander("Extraction details", expanded=True):
        render_extraction(result.get("extraction"))

    with st.expander("RAG validation"):
        render_rag_validation(result.get("rag_validation"))

    with st.expander("Raw JSON"):
        st.json(result)


def page_review_queue() -> None:
    st.header("Review Queue")
    st.caption("Purchase orders flagged for human review.")

    reviewer = st.text_input("Your email (reviewer)", value="procurement.manager@company.com")

    if st.button("Refresh queue", type="primary"):
        st.session_state.pop("review_queue", None)

    try:
        jobs = st.session_state.get("review_queue")
        if jobs is None:
            jobs = fetch_review_queue()
            st.session_state["review_queue"] = jobs
    except httpx.HTTPError as exc:
        st.error(f"Could not load review queue: {exc}")
        return

    if not jobs:
        st.success("No jobs pending review.")
        return

    st.metric("Pending review", len(jobs))

    for job in jobs:
        extraction = job.get("extraction") or {}
        vendor = extraction.get("vendor_name", "Unknown vendor")
        po_number = extraction.get("po_number") or "—"
        total = extraction.get("total_amount")

        with st.expander(f"{vendor} · PO {po_number} · {job.get('job_id', '')[:8]}…"):
            render_decision_banner(job)
            render_extraction(extraction)
            if job.get("reasons"):
                st.markdown("**Reasons:** " + " · ".join(job["reasons"]))
            render_rag_validation(job.get("rag_validation"))

            note = st.text_area("Review note", key=f"note_{job['job_id']}")
            btn1, btn2 = st.columns(2)
            if btn1.button("Approve", key=f"approve_{job['job_id']}", type="primary"):
                try:
                    updated = submit_review(job["job_id"], "approve", reviewer, note)
                    st.success(f"Approved — decision: {updated.get('decision')}")
                    st.session_state.pop("review_queue", None)
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(str(exc))
            if btn2.button("Reject", key=f"reject_{job['job_id']}"):
                try:
                    updated = submit_review(job["job_id"], "reject", reviewer, note)
                    st.warning(f"Rejected — decision: {updated.get('decision')}")
                    st.session_state.pop("review_queue", None)
                    st.rerun()
                except httpx.HTTPError as exc:
                    st.error(str(exc))


def page_job_history() -> None:
    st.header("Job History")
    limit = st.slider("Max jobs", 5, 50, 20)

    if st.button("Refresh jobs", type="primary"):
        st.session_state.pop("job_list", None)

    try:
        jobs = st.session_state.get("job_list")
        if jobs is None:
            jobs = fetch_jobs(limit=limit)
            st.session_state["job_list"] = jobs
    except httpx.HTTPError as exc:
        st.error(f"Could not load jobs: {exc}")
        return

    if not jobs:
        st.info("No jobs yet.")
        return

    rows = []
    for job in jobs:
        extraction = job.get("extraction") or {}
        rows.append(
            {
                "job_id": job.get("job_id"),
                "decision": job.get("decision"),
                "status": job.get("status"),
                "vendor": extraction.get("vendor_name"),
                "po_number": extraction.get("po_number"),
                "total_lkr": extraction.get("total_amount"),
                "confidence": job.get("confidence"),
            }
        )
    st.dataframe(rows, use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="PO Compliance Agent",
        page_icon="📋",
        layout="wide",
    )

    if "api_url" not in st.session_state:
        st.session_state["api_url"] = DEFAULT_API_URL

    st.sidebar.title("PO Compliance Agent")
    st.session_state["api_url"] = st.sidebar.text_input(
        "API URL",
        value=st.session_state["api_url"],
    )

    health = check_health()
    if health:
        status = health.get("status", "unknown")
        if status == "ok":
            st.sidebar.success(f"API: {status}")
        else:
            st.sidebar.warning(f"API: {status} (degraded)")
        st.sidebar.caption(
            f"Postgres: {health.get('postgres')} · Qdrant: {health.get('qdrant')}"
        )

    page = st.sidebar.radio(
        "Navigate",
        ["Process PO", "Review Queue", "Job History"],
    )

    if page == "Process PO":
        page_process_po()
    elif page == "Review Queue":
        page_review_queue()
    else:
        page_job_history()


if __name__ == "__main__":
    main()
