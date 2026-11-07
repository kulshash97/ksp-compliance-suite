from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.app.agents.whatsapp_bot import WhatsAppTaxAgent
from backend.app.core.payment_gateway import RazorpayPaymentManager
from backend.app.core.security import DataSecurityGuard
from backend.app.engines.gst_sales_matcher import GSTSalesReconciliationEngine
from backend.app.engines.itr_engine import ITREngine
from backend.app.engines.itr_json_exporter import generate_efiling_json
from backend.app.engines.itr_pdf_generator import generate_itr_computation_pdf
from backend.app.engines.statutory_guard import StatutoryAuditGatekeeper
from backend.app.models.schemas import EntityType

router = APIRouter(prefix="/api/v1", tags=["Autonomous Compliance & Monetization"])

payment_manager = RazorpayPaymentManager()
whatsapp_agent = WhatsAppTaxAgent()


# ==========================================
# 1. AUTONOMOUS COMPLIANCE & ITR AUDIT
# ==========================================

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


# ==========================================
# 2. MONETIZATION & RAZORPAY BILLING
# ==========================================

class OrderCreateRequest(BaseModel):
    tier: str
    client_email: str
    client_phone: str

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    tier: str

@router.post("/payments/create-order")
async def create_payment_order(req: OrderCreateRequest):
    """
    Creates an authenticated Razorpay order for ITR (₹499) or Firm Pass (₹2,499).
    """
    try:
        order_details = payment_manager.create_order(
            tier=req.tier,
            client_email=req.client_email,
            client_phone=req.client_phone
        )
        return {"status": "SUCCESS", "order": order_details}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/payments/verify")
async def verify_payment(req: PaymentVerifyRequest):
    """
    Validates HMAC-SHA256 signature and issues a cryptographically signed JWT access token.
    """
    is_valid = payment_manager.verify_payment_signature(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature. Transaction rejected.")

    validity = 720 if req.tier == "CA_FIRM_MONTHLY" else 24  # 30 days vs 24 hours
    token = payment_manager.generate_access_token(
        order_id=req.razorpay_order_id,
        payment_id=req.razorpay_payment_id,
        tier=req.tier,
        validity_hours=validity
    )
    return {
        "status": "PAYMENT_VERIFIED",
        "access_token": token,
        "validity_hours": validity,
        "message": "Payment verified. Full compliance suite access granted."
    }

@router.post("/payments/webhook")
async def razorpay_webhook(payload: dict):
    """
    Asynchronous webhook listener for Razorpay 'order.paid' events.
    """
    event = payload.get("event")
    if event == "order.paid":
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        order_id = order_entity.get("id")
        amount = order_entity.get("amount")
        return {"status": "ACKNOWLEDGED", "order_id": order_id, "amount_captured": amount}
    return {"status": "IGNORED"}


# ==========================================
# 3. WHATSAPP DOCUMENT INGESTION WEBHOOK
# ==========================================

@router.post("/webhooks/whatsapp", response_class=PlainTextResponse)
async def twilio_whatsapp_webhook(request: Request):
    """
    Receives incoming WhatsApp messages/attachments via Twilio,
    runs automated pre-audit in memory, and replies with an executive tax summary.
    """
    form_data = await request.form()
    twiml_reply = whatsapp_agent.process_incoming_message(dict(form_data))
    return PlainTextResponse(content=twiml_reply, media_type="application/xml")