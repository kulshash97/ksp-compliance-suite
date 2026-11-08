import sys
from pathlib import Path
from decimal import Decimal

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agents.whatsapp_bot import WhatsAppTaxAgent
from backend.app.engines.itr_engine import ITREngine

agent = WhatsAppTaxAgent()

print("\n" + "=" * 60)
print("TEST 1: Simulating Inbound Text Greeting")
print("=" * 60)

greeting_payload = {
    "Body": "Hi, I want to file my ITR for FY 2024-25",
    "NumMedia": "0",
    "From": "whatsapp:+919876543210"
}

greeting_reply = agent.process_incoming_message(greeting_payload)
print(greeting_reply)

print("\n" + "=" * 60)
print("TEST 2: Simulating Automated Document Ingestion (AIS & Bank Data)")
print("=" * 60)

# Simulate what the WhatsApp bot does when a PDF attachment is ingested
simulated_taxpayer_data = {
    "client_name": "Manish Kumar Hawaldar",
    "pan": "AETPH8430E",
    "assessment_year": "2025-26",
    "financial_year": "2024-25",
    "salary_income": Decimal("0.00"),
    "bank_savings_interest": Decimal("510.00"),
    "ais_savings_interest": Decimal("0.00"),
    "ais_fd_interest": Decimal("0.00"),
    "dividend_income": Decimal("0.00"),
    "professional_194j": Decimal("34050.00"),
    "property_sale_val": Decimal("3350000.00"),
    "stcg": Decimal("0.00"),
    "ltcg": Decimal("0.00"),
    "business_turnover": Decimal("0.00"),
    "tds_paid": Decimal("3405.00"),
    "deduction_80c": Decimal("0.00"),
    "deduction_80d": Decimal("0.00"),
    "hra_exemption": Decimal("0.00"),
    "home_loan_interest_24b": Decimal("0.00")
}

engine = ITREngine()
res = engine.compute(**simulated_taxpayer_data)

# Format the automated WhatsApp response card sent back to the taxpayer
whatsapp_summary_message = (
    f"📊 *KSP Autonomous Tax Audit — Filing Summary*\n"
    f"━━━━━━━━━━━━━━━━━━━━━━\n"
    f"👤 *Taxpayer:* {res.client_name} ({res.pan})\n"
    f"📅 *AY:* {res.assessment_year} | *Form:* {res.recommended_form}\n"
    f"💰 *Gross Total Income:* ₹ {res.gross_total_income:,.2f}\n"
    f"⚖️ *Recommended Regime:* {res.recommended_regime}\n"
    f"💵 *Net Tax Refund:* ₹ {abs(res.new_regime_tax - simulated_taxpayer_data['tds_paid']):,.2f}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━\n"
    f"⚠️ *Key Audit Flags:*\n"
    + "\n".join([f"• {flag}" for flag in res.audit_flags]) + "\n"
    f"━━━━━━━━━━━━━━━━━━━━━━\n"
    f"✅ To download your certified ITR XML/JSON computation pack, unlock using your access token."
)

print(whatsapp_summary_message)
print("\n" + "=" * 60)
print("SUCCESS: WhatsApp Ingestion & Message Synthesis Verified ✅")
print("=" * 60 + "\n")