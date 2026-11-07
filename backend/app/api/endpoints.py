from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from decimal import Decimal
from typing import Optional

from backend.app.engines.itr_engine import ITREngine
from backend.app.engines.gst_sales_matcher import GSTSalesReconciliationEngine
from backend.app.engines.statutory_guard import StatutoryAuditGatekeeper
from backend.app.engines.itr_pdf_generator import generate_itr_computation_pdf
from backend.app.engines.itr_json_exporter import generate_efiling_json
from backend.app.core.security import DataSecurityGuard
from backend.app.models.schemas import EntityType

router = APIRouter(prefix="/api/v1", tags=["Autonomous Compliance Engines"])

@router.post("/itr/audit-and-file")
async def audit_and_file_itr(
    bank_statement: UploadFile = File(...),
    ais_statement: Optional[UploadFile] = File(None),
    form_26as: Optional[UploadFile] = File(None),
    pdf_password: Optional[str] = Form(None),
    manual_salary: float = Form(0.0),
    deduction_80c: float = Form(0.0),
    deduction_80d: float = Form(0.0),
    home_loan_interest: float = Form(0.0)
):
    """
    Stateless, zero-disk endpoint: Ingests statements into volatile RAM,
    cross-audits dual tax regimes, and returns computation metrics and e-filing payloads.
    """
    itr_engine = ITREngine()

    # Read bank buffer into RAM
    bank_bytes = await bank_statement.read()
    b_text, _ = itr_engine.extract_text_from_pdf(bank_bytes, pdf_password)
    bank_data = itr_engine.parse_bank_statement(b_text)

    # Ingest AIS if provided
    ais_data = {"savings_interest": Decimal("0.00"), "tds": Decimal("0.00"), "receipts_194j": Decimal("0.00")}
    if ais_statement:
        ais_bytes = await ais_statement.read()
        ais_text, enc_err = itr_engine.extract_text_from_pdf(ais_bytes, pdf_password)
        if not enc_err:
            ais_data = itr_engine.parse_ais(ais_text)

    effective_salary = Decimal(str(manual_salary)) if manual_salary > 0 else bank_data["salary_inflow"]

    # Execute dual-regime optimization
    result = itr_engine.compute(
        client_name=bank_data.get("name") or "Taxpayer",
        pan=ais_data.get("pan") or "UNKNOWN_PAN",
        assessment_year=bank_data["assessment_year"],
        financial_year=bank_data["financial_year"],
        bank_savings_interest=bank_data["savings_interest"],
        ais_savings_interest=ais_data.get("savings_interest", Decimal("0.00")),
        ais_fd_interest=Decimal("0.00"),
        dividend_income=Decimal("0.00"),
        professional_194j=ais_data.get("receipts_194j", Decimal("0.00")),
        salary_income=effective_salary,
        tds_paid=ais_data.get("tds", Decimal("0.00")),
        deduction_80c=Decimal(str(deduction_80c)),
        deduction_80d=Decimal(str(deduction_80d)),
        hra_exemption=Decimal("0.00"),
        home_loan_interest_24b=Decimal(str(home_loan_interest))
    )

    json_payload = generate_efiling_json(result)

    return {
        "status": "SUCCESS",
        "client_name": DataSecurityGuard.sanitize_log(result.client_name),
        "pan": DataSecurityGuard.sanitize_log(result.pan),
        "assessment_year": result.assessment_year,
        "recommended_form": result.recommended_form,
        "recommended_regime": result.recommended_regime,
        "gross_total_income": float(result.gross_total_income),
        "tax_payable": float(result.new_regime_tax if "New" in result.recommended_regime else result.old_regime_tax),
        "tax_savings_vs_alternate": float(result.tax_savings),
        "efiling_json": json_payload,
        "audit_flags": result.audit_flags
    }