from enum import Enum
from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from typing import Optional, List

class EntityType(str, Enum):
    PROPRIETORSHIP = "PROPRIETORSHIP"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    PVT_LTD = "PVT_LTD"
    PUBLIC_LTD = "PUBLIC_LTD"

class AuditWorkflowStatus(str, Enum):
    NO_AUDIT_REQUIRED = "NO_AUDIT_REQUIRED"
    NEEDS_CA_AUDIT = "NEEDS_CA_AUDIT"

class ReconciliationStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    TAX_MISMATCH = "TAX_MISMATCH"
    MISSING_IN_2B = "MISSING_IN_2B"
    MISSING_IN_BOOKS = "MISSING_IN_BOOKS"

class StandardInvoice(BaseModel):
    invoice_number: str
    supplier_gstin: str
    supplier_name: Optional[str] = ""
    invoice_date: date
    taxable_value: Decimal
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    total_tax: Decimal
    total_value: Decimal

class ReconciliationRecord(BaseModel):
    status: ReconciliationStatus
    books_invoice: Optional[StandardInvoice] = None
    gstr2b_invoice: Optional[StandardInvoice] = None
    tax_variance: Decimal = Decimal("0.00")
    remarks: str = ""

class ReconciliationSummary(BaseModel):
    total_books_records: int
    total_gstr2b_records: int
    matched_count: int
    mismatched_count: int
    eligible_itc: Decimal
    ineligible_or_pending_itc: Decimal
    records: List[ReconciliationRecord]
    discrepancies: List[ReconciliationRecord]