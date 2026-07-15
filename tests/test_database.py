from app.models.decision import DecisionType, JobStatus
from app.models.process_order_response import ProcessOrderResponse
from app.models.purchase_order import LineItem, PurchaseOrder
from app.services import database_service


def test_save_and_get_job(db_session):
    extraction = PurchaseOrder(
        vendor_name="Ceylon Industrial Bearings (Pvt) Ltd",
        po_number="PO-4521-LK",
        total_amount=750_000.0,
        line_items=[
            LineItem(
                description="Ball bearing 22 mm",
                quantity=500,
                unit_price=1250.0,
                line_total=625_000.0,
            )
        ],
        extraction_confidence=1.0,
    )
    response = ProcessOrderResponse(
        job_id="job-test-db-001",
        status=JobStatus.COMPLETED,
        decision=DecisionType.PENDING_ROUTING,
        extraction=extraction,
        message="Saved for test",
    )

    database_service.save_job(
        db_session,
        response,
        filename="po_clean_ceylon_industrial.pdf",
        sender="vendor@test.com",
        subject="PO test",
    )

    record = database_service.get_job(db_session, "job-test-db-001")
    assert record is not None
    assert record.filename == "po_clean_ceylon_industrial.pdf"
    assert record.sender == "vendor@test.com"
    assert record.extraction_json["po_number"] == "PO-4521-LK"

    restored = database_service.job_to_response(record)
    assert restored.job_id == "job-test-db-001"
    assert restored.extraction is not None
    assert restored.extraction.po_number == "PO-4521-LK"


def test_list_jobs(db_session):
    for index in range(2):
        database_service.save_job(
            db_session,
            ProcessOrderResponse(
                job_id=f"job-list-{index}",
                status=JobStatus.COMPLETED,
                decision=DecisionType.PENDING_ROUTING,
            ),
        )

    jobs = database_service.list_jobs(db_session, limit=10)
    assert len(jobs) == 2
