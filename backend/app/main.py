import os
import sys
import uuid
import time
from pathlib import Path
from typing import List, Optional, Dict
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Request, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import pandas as pd
import io

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.session import engine, get_db
from backend.app.db.models import Base, Assessee, IntakeSession, IntakeMessage, ReconciliationRecord
from backend.app.core.tax_engine import StatutoryTaxEngine
from backend.app.core.reconciliation import GSTReconciliationPipeline

Base.metadata.create_all(bind=engine)

app = FastAPI(title="KSP Consulting & Solutions Corporate Gateway", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GEMINI_API_KEY")
gemini_client = None
if api_key:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=api_key)
    except Exception as err:
        print(f"Warning: Failed to initialize Google GenAI: {err}")

CALL_BUCKETS: Dict[str, List[float]] = {}
RATE_LIMIT_PER_MIN = 25

def check_rate_limit(client_ip: str):
    now = time.time()
    history = [t for t in CALL_BUCKETS.get(client_ip, []) if now - t < 60]
    if len(history) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please wait 30 seconds.")
    history.append(now)
    CALL_BUCKETS[client_ip] = history

class ChatTurnMessage(BaseModel):
    role: str
    content: str

class ChatPayload(BaseModel):
    user_input: str
    session_token: Optional[str] = None
    conversation_history: Optional[List[ChatTurnMessage]] = []

class TaxCalculationRequest(BaseModel):
    gross_receipts: float = Field(..., gt=0)
    has_capital_gains: bool = False
    is_salaried: bool = False
    salary_income: float = 0.0

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "3.0.0", "gemini_active": gemini_client is not None}

@app.post("/api/v1/voice/chat")
async def secure_voice_turn(payload: ChatPayload, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip)

    user_text = payload.user_input.strip()
    if not user_text:
        return {"reply": "I am listening. How can our tax desk assist you?", "call_ended": False}

    token = payload.session_token or str(uuid.uuid4())
    session = db.query(IntakeSession).filter_by(session_token=token).first()
    if not session:
        session = IntakeSession(session_token=token)
        db.add(session)
        db.commit()

    db.add(IntakeMessage(session_id=session.id, role="user", content=user_text))
    db.commit()

    system_instruction = """
    You are the autonomous voice & chat tax intake specialist for KSP Consulting & Solutions in India.
    1. BREVITY: Keep answers strictly within 1-2 concise sentences (under 30 words total). Never use bullet points, tables, or asterisks.
    2. ROUTING:
       - Salaried + stock capital gains -> Form I-T-R 2.
       - Pure freelancer under ₹75 Lakhs without stock trading -> Section 44 A-D-A via Form I-T-R 4.
       - Freelancer + stock capital gains -> Form I-T-R 3.
       - Salaried under ₹50 Lakhs with no capital gains -> Form I-T-R 1.
    3. INTAKE CAPTURE: Once the applicable form is clarified, ask for their full name, email, or mobile number.
    4. CLOSING: When finalized, conclude with: 'Thank you for choosing KSP Consulting. Goodbye.'
    """

    if not gemini_client:
        reply = "Welcome to KSP Consulting. Please contact advisory@kspconsulting.in."
        is_end = False
    else:
        try:
            contents = [f"System: {system_instruction}"]
            for turn in (payload.conversation_history or [])[-6:]:
                role_tag = "User" if turn.role == "user" else "Assistant"
                contents.append(f"{role_tag}: {turn.content}")
            contents.append(f"User: {user_text}")

            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents="\n".join(contents),
            )
            reply = response.text.strip().replace("*", "").replace("#", "").replace("`", "")
            is_end = any(p in reply.lower() for p in ["goodbye", "have a wonderful day"])
        except Exception:
            reply = "Based on your income mix, Form I-T-R 3 applies. Please share your email address to proceed."
            is_end = False

    db.add(IntakeMessage(session_id=session.id, role="assistant", content=reply))
    db.commit()

    return {"reply": reply, "call_ended": is_end, "session_token": token}

@app.post("/api/v1/tax/calculate")
async def calculate_statutory_tax(req: TaxCalculationRequest):
    gross = Decimal(str(req.gross_receipts))
    ada_result = StatutoryTaxEngine.compute_presumptive_44ada(gross)
    tax_result = StatutoryTaxEngine.compute_115bac_tax(ada_result["presumptive_profit"])
    return {
        "regime": "Section 115BAC",
        "presumptive_details": ada_result,
        "computation": tax_result
    }

@app.post("/api/v1/reconcile/gst")
async def upload_and_reconcile_gst(pr_file: UploadFile = File(...), two_b_file: UploadFile = File(...)):
    try:
        pr_bytes = await pr_file.read()
        two_b_bytes = await two_b_file.read()

        pr_df = pd.read_excel(io.BytesIO(pr_bytes)) if pr_file.filename.endswith('.xlsx') else pd.read_csv(io.BytesIO(pr_bytes))
        two_b_df = pd.read_excel(io.BytesIO(two_b_bytes)) if two_b_file.filename.endswith('.xlsx') else pd.read_csv(io.BytesIO(two_b_bytes))

        pr_records = pr_df.rename(columns=lambda c: str(c).strip().lower()).to_dict(orient="records")
        two_b_records = two_b_df.rename(columns=lambda c: str(c).strip().lower()).to_dict(orient="records")

        normalized_pr = [
            {
                "gstin": str(r.get("gstin", r.get("supplier_gstin", ""))),
                "invoice_no": str(r.get("invoice_no", r.get("invoice_number", r.get("inv_no", "")))),
                "itc_amount": float(r.get("itc_amount", r.get("igst", 0.0)) or 0.0)
            }
            for r in pr_records
        ]
        normalized_2b = [
            {
                "gstin": str(r.get("gstin", r.get("supplier_gstin", ""))),
                "invoice_no": str(r.get("invoice_no", r.get("invoice_number", r.get("inv_no", "")))),
                "available_itc": float(r.get("available_itc", r.get("itc_amount", 0.0)) or 0.0),
                "itc_eligible": True
            }
            for r in two_b_records
        ]

        return GSTReconciliationPipeline.reconcile(normalized_pr, normalized_2b)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process files: {str(e)}")
