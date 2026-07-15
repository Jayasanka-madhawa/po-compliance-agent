from __future__ import annotations

import re
from functools import lru_cache

from openai import OpenAI
from qdrant_client import QdrantClient

from app.config import settings
from app.models.decision import (
    MathValidation,
    PaymentTermsCheck,
    RagValidation,
    SpendingCheck,
    VendorCheck,
)
from app.models.purchase_order import PurchaseOrder

POLICY_MAX_AUTO_APPROVE_DAYS = 30
AUTO_APPROVE_LIMIT_LKR = 1_000_000.0
MANAGER_REVIEW_LIMIT_LKR = 5_000_000.0
MATH_TOLERANCE = 0.01


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _parse_vendor_chunk(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for key in ("vendor_id", "legal_name", "aliases", "status"):
        match = re.search(rf"{key}=([^,]+)", text)
        if match:
            parts[key] = match.group(1).strip()
    return parts


def _vendor_names_match(extracted_name: str, legal_name: str, aliases: str) -> bool:
    extracted = _normalize(extracted_name)
    if not extracted:
        return False

    candidates = [legal_name, *aliases.split("|")]
    for candidate in candidates:
        normalized = _normalize(candidate)
        if not normalized:
            continue
        if normalized in extracted or extracted in normalized:
            return True
    return False


@lru_cache(maxsize=1)
def _qdrant_client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


@lru_cache(maxsize=1)
def _openai_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key)


def search_qdrant(query: str, limit: int = 3) -> list[dict]:
    embedding = (
        _openai_client()
        .embeddings.create(
            model=settings.openai_embedding_model,
            input=query,
        )
        .data[0]
        .embedding
    )

    hits = _qdrant_client().search(
        collection_name=settings.qdrant_collection,
        query_vector=embedding,
        limit=limit,
    )

    return [
        {
            "text": hit.payload.get("text", ""),
            "source_doc": hit.payload.get("source_doc"),
            "score": hit.score,
        }
        for hit in hits
        if hit.payload
    ]


def validate_math(po: PurchaseOrder) -> MathValidation:
    line_items_sum = round(sum(item.line_total for item in po.line_items), 2)
    declared_subtotal = po.subtotal

    if declared_subtotal is None:
        return MathValidation(
            line_items_sum=line_items_sum,
            declared_subtotal=None,
            total_reconciled=True,
            variance_pct=None,
        )

    if declared_subtotal == 0:
        total_reconciled = line_items_sum == 0
        variance_pct = None if total_reconciled else 1.0
    else:
        variance_pct = abs(line_items_sum - declared_subtotal) / declared_subtotal
        total_reconciled = variance_pct <= MATH_TOLERANCE

    return MathValidation(
        line_items_sum=line_items_sum,
        declared_subtotal=declared_subtotal,
        total_reconciled=total_reconciled,
        variance_pct=round(variance_pct, 4) if variance_pct is not None else None,
    )


def check_vendor(vendor_name: str, hits: list[dict]) -> VendorCheck:
    best_score = 0.0
    best_match: VendorCheck | None = None

    for hit in hits:
        if hit.get("source_doc") != "approved_vendors.csv":
            continue

        parsed = _parse_vendor_chunk(hit["text"])
        if parsed.get("status") != "approved":
            continue

        if not _vendor_names_match(
            vendor_name,
            parsed.get("legal_name", ""),
            parsed.get("aliases", ""),
        ):
            continue

        score = float(hit.get("score") or 0.0)
        if best_match is None or score > best_score:
            best_score = score
            best_match = VendorCheck(
                status="approved",
                vendor_id=parsed.get("vendor_id"),
                matched_name=parsed.get("legal_name"),
                match_confidence=min(max(score, 0.0), 1.0),
                source_doc=hit.get("source_doc"),
            )

    if best_match:
        return best_match

    return VendorCheck(
        status="unapproved",
        matched_name=vendor_name,
        source_doc="approved_vendors.csv",
    )


def check_payment_terms(
    payment_terms_days: int | None,
    hits: list[dict],
) -> PaymentTermsCheck:
    source_doc = next(
        (hit["source_doc"] for hit in hits if hit.get("source_doc") == "payment_policy.md"),
        "payment_policy.md",
    )

    if payment_terms_days is None:
        return PaymentTermsCheck(
            status="requires_review",
            extracted_terms_days=None,
            policy_max_auto_approve_days=POLICY_MAX_AUTO_APPROVE_DAYS,
            source_doc=source_doc,
        )

    if payment_terms_days <= POLICY_MAX_AUTO_APPROVE_DAYS:
        status = "approved"
    else:
        status = "requires_review"

    return PaymentTermsCheck(
        status=status,
        extracted_terms_days=payment_terms_days,
        policy_max_auto_approve_days=POLICY_MAX_AUTO_APPROVE_DAYS,
        source_doc=source_doc,
    )


def check_spending(total_amount: float, hits: list[dict]) -> SpendingCheck:
    source_doc = next(
        (
            hit["source_doc"]
            for hit in hits
            if hit.get("source_doc") == "approval_policy.md"
        ),
        "approval_policy.md",
    )

    if total_amount <= AUTO_APPROVE_LIMIT_LKR:
        status = "auto_approve_eligible"
        limit = AUTO_APPROVE_LIMIT_LKR
    elif total_amount <= MANAGER_REVIEW_LIMIT_LKR:
        status = "manager_review"
        limit = MANAGER_REVIEW_LIMIT_LKR
    else:
        status = "director_review"
        limit = MANAGER_REVIEW_LIMIT_LKR

    return SpendingCheck(
        status=status,
        total_amount=total_amount,
        limit=limit,
        source_doc=source_doc,
    )


def _collect_issues(
    vendor_check: VendorCheck,
    payment_terms_check: PaymentTermsCheck,
    spending_check: SpendingCheck,
    math_validation: MathValidation,
) -> list[str]:
    issues: list[str] = []

    if vendor_check.status != "approved":
        issues.append("unknown_vendor")

    if payment_terms_check.extracted_terms_days is None:
        issues.append("payment_terms_missing")
    elif payment_terms_check.status == "requires_review":
        issues.append("payment_terms_exceed_policy")

    if spending_check.status in {"manager_review", "director_review"}:
        issues.append("amount_requires_review")

    if not math_validation.total_reconciled:
        issues.append("subtotal_mismatch")

    return issues


def validate_purchase_order(po: PurchaseOrder) -> RagValidation:
    queries = [
        f"approved vendor {po.vendor_name}",
        f"payment terms {po.payment_terms_days or 'missing'} days auto approve policy",
        f"spending limit auto approve {po.total_amount} LKR",
    ]

    vendor_hits = search_qdrant(queries[0])
    payment_hits = search_qdrant(queries[1])
    spending_hits = search_qdrant(queries[2])

    vendor_check = check_vendor(po.vendor_name, vendor_hits)
    payment_terms_check = check_payment_terms(po.payment_terms_days, payment_hits)
    spending_check = check_spending(po.total_amount, spending_hits)
    math_validation = validate_math(po)

    issues = _collect_issues(
        vendor_check,
        payment_terms_check,
        spending_check,
        math_validation,
    )

    confidence = 0.95 if not issues else max(0.55, 0.95 - 0.1 * len(issues))

    return RagValidation(
        vendor_check=vendor_check,
        payment_terms_check=payment_terms_check,
        spending_check=spending_check,
        math_validation=math_validation,
        rag_queries_used=queries,
        issues=issues,
        overall_rag_confidence=round(confidence, 2),
    )