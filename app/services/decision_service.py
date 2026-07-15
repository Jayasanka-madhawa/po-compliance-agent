from app.models.decision import (
    DecisionType,
    JobStatus,
    ProcessingResult,
    RagValidation,
)
from app.models.purchase_order import PurchaseOrder

MIN_AUTO_ACCEPT_CONFIDENCE = 0.75

ISSUE_REASONS: dict[str, str] = {
    "unknown_vendor": "Vendor is not on the approved vendor list",
    "payment_terms_missing": "Payment terms were not provided",
    "payment_terms_exceed_policy": "Payment terms exceed the auto-approve limit (30 days)",
    "amount_requires_review": "Order amount requires manager or director approval",
    "subtotal_mismatch": "Line item totals do not reconcile with declared subtotal",
}


def _reasons_from_issues(issues: list[str]) -> list[str]:
    return [ISSUE_REASONS.get(issue, issue.replace("_", " ")) for issue in issues]


def route_decision(
    job_id: str,
    extraction: PurchaseOrder,
    rag_validation: RagValidation,
) -> ProcessingResult:
    reasons: list[str] = []

    if rag_validation.issues:
        reasons.extend(_reasons_from_issues(rag_validation.issues))

    if extraction.extraction_confidence < MIN_AUTO_ACCEPT_CONFIDENCE:
        reasons.append(
            f"Extraction confidence ({extraction.extraction_confidence:.0%}) "
            f"is below the {MIN_AUTO_ACCEPT_CONFIDENCE:.0%} threshold"
        )

    if extraction.fields_missing:
        for field in extraction.fields_missing:
            reasons.append(f"Required field missing: {field}")

    if reasons:
        decision = DecisionType.HUMAN_REVIEW
        explanation = "Purchase order requires human review: " + "; ".join(reasons)
    else:
        decision = DecisionType.AUTO_ACCEPT
        explanation = (
            "Purchase order meets all compliance checks and is eligible "
            "for automatic acceptance."
        )

    rag_confidence = rag_validation.overall_rag_confidence or 0.0
    confidence = round(min(extraction.extraction_confidence, rag_confidence), 2)

    return ProcessingResult(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        decision=decision,
        confidence=confidence,
        extraction=extraction,
        rag_validation=rag_validation,
        reasons=reasons,
        explanation=explanation,
        message="Processing complete.",
    )
