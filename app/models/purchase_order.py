from pydantic import BaseModel, Field


class LineItem(BaseModel):
    sku: str | None = None
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)


class PurchaseOrder(BaseModel):
    vendor_name: str
    po_number: str | None = None
    po_date: str | None = None
    buyer_name: str | None = None
    currency: str = "LKR"
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float | None = None
    tax: float | None = None
    shipping: float | None = None
    total_amount: float = Field(ge=0)
    payment_terms: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0)
    delivery_date: str | None = None
    notes: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    fields_missing: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)