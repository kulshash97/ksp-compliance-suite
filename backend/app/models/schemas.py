from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ComplianceStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISSING_IN_BOOKS = "MISSING_IN_BOOKS"
    MISSING_IN_2B = "MISSING_IN_2B"

class AuditWorkflowStatus(str, Enum):
    SELF_SERVE = "SELF_SERVE"
    NEEDS_CA_AUDIT = "NEEDS_CA_AUDIT"
    CA_REVIEW_PENDING = "CA_REVIEW_PENDING"
    CA_APPROVED = "CA_APPROVED"
    CA_REJECTED = "CA_REJECTED"

class EntityType(str, Enum):
    PROPRIETORSHIP = "PROPRIETORSHIP"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    PVT_LTD = "PVT_LTD"
    PUBLIC_LTD = "PUBLIC_LTD"

class StandardInvoice(BaseModel):
    invoice_number: str
    supplier_gstin: str
    supplier_name: Optional[str] = None
    invoice_date: date
    taxable_value: Decimal = Field(decimal_places=2)
    cgst: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    sgst: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    igst: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_tax: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    total_value: Decimal = Field(decimal_places=2)

    @field_validator("supplier_gstin")
    @classmethod
    def validate_gstin(cls, v: str) -> str:
        clean = v.strip().upper()
        if len(clean) != 15:
            raise ValueError(f"Invalid GSTIN length ({len(clean)}). Must be 15 chars.")
        return clean

class ReconciliationRecord(BaseModel):
    invoice_number: str
    supplier_gstin: str
    status: ComplianceStatus
    books_taxable: Optional[Decimal] = None
    gstr2b_taxable: Optional[Decimal] = None
    books_tax: Optional[Decimal] = None
    gstr2b_tax: Optional[Decimal] = None
    tax_difference: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    match_score: float = 1.0
    notes: str = ""

class ReconciliationSummary(BaseModel):
    total_books_records: int
    total_2b_records: int
    matched_count: int
    partial_match_count: int
    missing_in_books_count: int
    missing_in_2b_count: int
    eligible_itc: Decimal
    ineligible_or_pending_itc: Decimal
    discrepancies: List[ReconciliationRecord]
