from datetime import date
from decimal import Decimal
from backend.app.models.schemas import StandardInvoice
from backend.app.engines.gst_matcher import Rule36ReconciliationEngine

engine = Rule36ReconciliationEngine()

books_sample = [
    StandardInvoice(
        invoice_number="INV/2026/001",
        supplier_gstin="36AAAAA0000A1Z5",
        invoice_date=date(2026, 4, 10),
        taxable_value=Decimal("10000.00"),
        cgst=Decimal("900.00"),
        sgst=Decimal("900.00"),
        total_tax=Decimal("1800.00"),
        total_value=Decimal("11800.00")
    ),
    StandardInvoice(
        invoice_number="INV-002",
        supplier_gstin="36AAAAA0000A1Z5",
        invoice_date=date(2026, 4, 12),
        taxable_value=Decimal("5000.00"),
        cgst=Decimal("450.00"),
        sgst=Decimal("450.00"),
        total_tax=Decimal("900.00"),
        total_value=Decimal("5900.00")
    )
]

gstr2b_sample = [
    StandardInvoice(
        invoice_number="INV2026001",  # Stripped slash, matches via normalization
        supplier_gstin="36AAAAA0000A1Z5",
        invoice_date=date(2026, 4, 10),
        taxable_value=Decimal("10000.00"),
        cgst=Decimal("900.00"),
        sgst=Decimal("900.00"),
        total_tax=Decimal("1800.00"),
        total_value=Decimal("11800.00")
    )
]

summary = engine.run(books_sample, gstr2b_sample)
print(f"--- RECONCILIATION RESULT ---")
print(f"Total Books: {summary.total_books_records} | Total 2B: {summary.total_2b_records}")
print(f"Matched: {summary.matched_count} | Eligible ITC: Rs {summary.eligible_itc}")
print(f"Missing in 2B: {summary.missing_in_2b_count} | Blocked/Pending ITC: Rs {summary.ineligible_or_pending_itc}")
