import os
import io
import requests
from decimal import Decimal
from twilio.twiml.messaging_response import MessagingResponse
from backend.app.engines.itr_engine import ITREngine
from backend.app.engines.itr_json_exporter import generate_efiling_json
from backend.app.core.security import DataSecurityGuard

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC_placeholder")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "placeholder_token")

class WhatsAppTaxAgent:
    def __init__(self):
        self.itr_engine = ITREngine()

    def process_incoming_message(self, form_data: dict) -> str:
        """
        Handles incoming WhatsApp messages. Detects PDF media attachments (Bank statements / Form 16),
        parses financial credits, and replies with an executive tax summary.
        """
        response = MessagingResponse()
        msg = response.message()

        body = form_data.get("Body", "").strip()
        num_media = int(form_data.get("NumMedia", 0))
        sender_phone = form_data.get("From", "")

        # Case 1: Text-only greeting or help query
        if num_media == 0:
            msg.body(
                "👋 *Welcome to KSP Autonomous Tax Desk*\n\n"
                "To get an instant Dual-Regime Tax Audit:\n"
                "1️⃣ Send your *Bank Statement (PDF)* or *Form 16*\n"
                "2️⃣ If password-protected, include the password in your message (e.g., `pass: pan+dob`)\n\n"
                "_All processing runs in volatile RAM under zero-disk DPDPA standards._"
            )
            return str(response)

        # Case 2: Document Ingestion
        media_url = form_data.get("MediaUrl0")
        media_type = form_data.get("MediaContentType0", "")

        if "pdf" not in media_type.lower():
            msg.body("⚠️ Please upload a valid PDF document (Bank Statement, AIS, or Form 16).")
            return str(response)

        # Download media into in-memory stream using Twilio basic auth
        pdf_password = None
        if "pass:" in body.lower():
            pdf_password = body.split("pass:")[1].strip()

        try:
            req = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=20)
            pdf_bytes = req.content

            b_text, enc_err = self.itr_engine.extract_text_from_pdf(pdf_bytes, pdf_password)
            if enc_err:
                msg.body("🔒 PDF is password protected. Please reply with: `pass: <your_password>` alongside the document.")
                return str(response)

            b_data = self.itr_engine.parse_bank_statement(b_text)
            
            # Execute automated audit
            res = self.itr_engine.compute(
                client_name=b_data.get("name") or "Taxpayer",
                pan="PROVIDED_VIA_WA",
                assessment_year=b_data["assessment_year"],
                financial_year=b_data["financial_year"],
                bank_savings_interest=b_data["savings_interest"],
                ais_savings_interest=Decimal("0.00"),
                ais_fd_interest=Decimal("0.00"),
                dividend_income=Decimal("0.00"),
                professional_194j=Decimal("0.00"),
                salary_income=b_data["salary_inflow"],
                tds_paid=Decimal("0.00"),
                deduction_80c=Decimal("0.00"),
                deduction_80d=Decimal("0.00"),
                hra_exemption=Decimal("0.00"),
                home_loan_interest_24b=Decimal("0.00")
            )

            msg.body(
                f"✅ *Audit Completed for {res.client_name}*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Assessment Year:* {res.assessment_year}\n"
                f"• *Annual Payroll Inflow:* ₹{res.salary_income:,.2f}\n"
                f"• *Savings Interest:* ₹{res.savings_interest_bank:,.2f}\n"
                f"• *Recommended Regime:* {res.recommended_regime}\n"
                f"• *Computed Tax Liability:* ₹{res.new_regime_tax if 'New' in res.recommended_regime else res.old_regime_tax:,.2f}\n\n"
                f"📄 *Download Filing-Ready Tax Pack (CBDT JSON + PDF):*\n"
                f"https://ksp-compliance-suite.onrender.com/#pricing-section\n\n"
                f"_Reply 'FILE' to speak with a Chartered Accountant._"
            )
        except Exception as e:
            msg.body(f"❌ Document parsing error: {str(e)[:100]}. Please ensure the PDF is clear.")

        return str(response)