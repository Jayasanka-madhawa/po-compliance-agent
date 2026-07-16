# Required Purchase Order Fields

## Mandatory for auto-accept
- Vendor legal name (must match approved vendor list)
- PO number or vendor reference
- Order date
- At least one line item with description, quantity, unit price, and line total
- Total amount and payment terms
- Delivery location or ship-to address

## Triggers human review when missing
- PO number missing
- Payment terms missing or ambiguous
- Subtotal does not reconcile with line items (tolerance 1%)
- Buyer company name missing on vendor-issued PO

## Optional but recommended
- Requested delivery date
- Buyer contact name and email
- Tax registration number (VAT) for orders above LKR 500,000
- Project or cost centre code
