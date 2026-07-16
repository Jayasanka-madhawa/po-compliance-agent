from app.models.decision import DecisionType, JobStatus
from app.models.process_order_response import ProcessOrderResponse
from app.models.purchase_order import LineItem, PurchaseOrder
from app.models.review import ReviewAction
from app.services import database_service


def _human_review_job(job_id: str, vendor_name: str) -> ProcessOrderResponse:
    return ProcessOrderResponse(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        decision=DecisionType.HUMAN_REVIEW,
        confidence=0.7,
        extraction=PurchaseOrder(
            vendor_name=vendor_name,
            po_number="SHP-2026-044",
            total_amount=14_775_000.0,
            line_items=[
                LineItem(
                    description="Hydraulic pump",
                    quantity=1,
                    unit_price=14_775_000.0,
                    line_total=14_775_000.0,
                )
            ],
            extraction_confidence=0.9,
        ),
        reasons=["Vendor is not on the approved vendor list"],
        message="Processing complete.",
    )


def test_list_review_queue_only_human_review(db_session):
    database_service.save_job(
        db_session,
        ProcessOrderResponse(
            job_id="job-auto",
            status=JobStatus.COMPLETED,
            decision=DecisionType.AUTO_ACCEPT,
        ),
    )
    database_service.save_job(
        db_session,
        ProcessOrderResponse(
            job_id="job-manual",
            status=JobStatus.COMPLETED,
            decision=DecisionType.MANUALLY_APPROVED,
        ),
    )
    database_service.save_job(
        db_session,
        _human_review_job("job-review-1", "Serendib Heavy Parts Ltd"),
    )

    queue = database_service.list_review_queue(db_session)
    assert len(queue) == 1
    assert queue[0].id == "job-review-1"


def test_list_review_queue_vendor_filter(db_session):
    database_service.save_job(
        db_session,
        _human_review_job("job-serendib", "Serendib Heavy Parts Ltd"),
    )
    database_service.save_job(
        db_session,
        _human_review_job("job-lakpura", "Lakpura Logistics (Pvt) Ltd"),
    )

    queue = database_service.list_review_queue(db_session, vendor="Lakpura")
    assert len(queue) == 1
    assert queue[0].id == "job-lakpura"


def test_apply_review_approve(db_session):
    database_service.save_job(
        db_session,
        _human_review_job("job-approve", "Serendib Heavy Parts Ltd"),
    )

    record = database_service.apply_review(
        db_session,
        "job-approve",
        action=ReviewAction.APPROVE,
        reviewer="procurement.manager@company.com",
        note="Approved after vendor verification call",
    )

    assert record.decision == DecisionType.MANUALLY_APPROVED.value
    assert record.reviewer == "procurement.manager@company.com"
    assert record.review_note == "Approved after vendor verification call"
    assert record.reviewed_at is not None


def test_apply_review_reject(db_session):
    database_service.save_job(
        db_session,
        _human_review_job("job-reject", "Serendib Heavy Parts Ltd"),
    )

    record = database_service.apply_review(
        db_session,
        "job-reject",
        action=ReviewAction.REJECT,
        reviewer="procurement.manager@company.com",
        note="Vendor not authorized for this category",
    )

    assert record.decision == DecisionType.REJECTED.value
    assert "Rejected by" in (record.message or "")


def test_apply_review_not_pending_raises(db_session):
    database_service.save_job(
        db_session,
        ProcessOrderResponse(
            job_id="job-auto-2",
            status=JobStatus.COMPLETED,
            decision=DecisionType.AUTO_ACCEPT,
        ),
    )

    try:
        database_service.apply_review(
            db_session,
            "job-auto-2",
            action=ReviewAction.APPROVE,
            reviewer="reviewer@test.com",
        )
        raised = False
    except ValueError:
        raised = True

    assert raised


def test_get_review_queue_api(client, db_session):
    database_service.save_job(
        db_session,
        _human_review_job("job-api-review", "Serendib Heavy Parts Ltd"),
    )
    database_service.save_job(
        db_session,
        ProcessOrderResponse(
            job_id="job-api-auto",
            status=JobStatus.COMPLETED,
            decision=DecisionType.AUTO_ACCEPT,
        ),
    )

    response = client.get("/review-queue")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job_id"] == "job-api-review"
    assert body[0]["decision"] == DecisionType.HUMAN_REVIEW.value
    assert body[0]["reasons"]


def test_review_job_approve_api(client, db_session):
    database_service.save_job(
        db_session,
        _human_review_job("job-patch-approve", "Serendib Heavy Parts Ltd"),
    )

    response = client.patch(
        "/jobs/job-patch-approve/review",
        json={
            "action": "approve",
            "reviewer": "procurement.manager@company.com",
            "note": "Approved exception for one-time purchase",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == DecisionType.MANUALLY_APPROVED.value
    assert body["reviewer"] == "procurement.manager@company.com"
    assert body["review_note"] == "Approved exception for one-time purchase"
    assert body["reviewed_at"] is not None

    queue_response = client.get("/review-queue")
    assert queue_response.json() == []


def test_review_job_not_found(client):
    response = client.patch(
        "/jobs/missing-job/review",
        json={"action": "approve", "reviewer": "reviewer@test.com"},
    )
    assert response.status_code == 404


def test_review_job_not_pending(client, db_session):
    database_service.save_job(
        db_session,
        ProcessOrderResponse(
            job_id="job-not-pending",
            status=JobStatus.COMPLETED,
            decision=DecisionType.AUTO_ACCEPT,
        ),
    )

    response = client.patch(
        "/jobs/job-not-pending/review",
        json={"action": "reject", "reviewer": "reviewer@test.com"},
    )
    assert response.status_code == 400
