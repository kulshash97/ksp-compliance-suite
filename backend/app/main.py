import os
import re
import io
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="KSP Compliance Engine")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

sessions: Dict[str, Dict] = {}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
gemini_client = None

if GEMINI_API_KEY:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("✅ Gemini API Client Initialized Successfully!")
    except Exception as ex:
        print(f"⚠️ Gemini Init Warning: {ex}")

class MessageTurn(BaseModel):
    role: str
    content: str

class VoiceRequest(BaseModel):
    session_id: Optional[str] = "default_client"
    message: str
    language: Optional[str] = "hi-IN"
    history: Optional[List[MessageTurn]] = []

def extract_valid_contact(text: str):
    clean = text.replace(" at the rate ", "@").replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
    phone_candidates = re.findall(r'(?:(?:\+|0{0,2})91(\d{10}))|(?<!\d)(\d{10})(?!\d)', clean)
    phone = None
    if phone_candidates:
        match = phone_candidates[0]
        phone = match[0] or match[1]

    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', clean)
    email = email_match.group(0) if email_match else None
    return phone, email

def normalize_spoken_text(text: str, lang_code: str) -> str:
    if "hi" in lang_code:
        text = re.sub(r'2\s*[-–]\s*4\s*घंटे?', 'दो से चार घंटे', text)
        text = text.replace("2-4", "दो से चार")
    elif "te" in lang_code:
        text = re.sub(r'2\s*[-–]\s*4\s*గంట', 'రెండు నుండి నాలుగు గంట', text)
        text = text.replace("2-4", "రెండు నుండి నాలుగు")
    elif "kn" in lang_code:
        text = re.sub(r'2\s*[-–]\s*4\s*ಗಂಟೆ', 'ಎರಡರಿಂದ ನಾಲ್ಕು ಗಂಟೆ', text)
        text = text.replace("2-4", "ಎರಡರಿಂದ ನಾಲ್ಕು")
    elif "mr" in lang_code:
        text = re.sub(r'2\s*[-–]\s*4\s*तास', 'दोन ते चार तास', text)
        text = text.replace("2-4", "दोन ते चार")
    else:
        text = re.sub(r'2\s*[-–]\s*4\s*hours?', '2 to 4 hours', text)
        text = text.replace("2-4", "2 to 4")
    return text

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    template_file = TEMPLATES_DIR / "landing_page.html"
    if template_file.exists():
        return templates.TemplateResponse(request=request, name="landing_page.html")
    return HTMLResponse("<h2>KSP Compliance Suite is Running.</h2>")

@app.post("/api/voice/intake")
async def voice_intake(payload: VoiceRequest):
    sid = payload.session_id or "default_client"
    if sid not in sessions:
        sessions[sid] = {
            "name": "Taxpayer",
            "phone": None,
            "email": None,
            "sources": [],
            "recommended_form": "ITR-2",
            "contact_saved": False
        }

    state = sessions[sid]
    user_msg = payload.message.strip()
    msg_lower = user_msg.lower()

    extracted_phone, extracted_email = extract_valid_contact(user_msg)
    if extracted_phone:
        state["phone"] = extracted_phone
    if extracted_email:
        state["email"] = extracted_email

    if any(w in msg_lower for w in ["rent", "rental", "किराया", "house", "लैंड", "land", "రెంట్", "అద్దె"]):
        if "Income from House Property (Rental)" not in state["sources"]:
            state["sources"].append("Income from House Property (Rental)")
        state["recommended_form"] = "ITR-2"

    if any(w in msg_lower for w in ["stock", "share", "मार्केट", "म्यूचुअल फंड", "capital gain", "షేర్లు"]):
        if "Capital Gains (Equity/Stocks)" not in state["sources"]:
            state["sources"].append("Capital Gains (Equity/Stocks)")
        state["recommended_form"] = "ITR-2"

    if any(w in msg_lower for w in ["salary", "वेतन", "सैलरी", "జీతం"]):
        if "Salary Income" not in state["sources"]:
            state["sources"].append("Salary Income")

    closing_keywords = ["thank you", "thanks", "dhanyawad", "dhanyavadagalu", "chala thanks", "dhanyavaad", "bye", "goodbye", "nothing else", "that's all", "धन्यवाद", "ओके धन्यवाद", "अच्छा धन्यवाद"]
    is_closing = any(k in msg_lower for k in closing_keywords)

    lang_code = payload.language or "hi-IN"

    sys_instruction = f"""
You are the senior autonomous tax advisor at KSP Consulting & Solutions, Hyderabad, India.
CRITICAL LANGUAGE INSTRUCTION:
- Respond in the EXACT script and language requested: {lang_code}.
- If Hindi, use polite Hindi (आप form).
- Phrasing for ranges: NEVER use hyphens like 2-4. Always spell out: "दो से चार घंटे".
- Applicable Form: {state['recommended_form']}. Fee: ₹2,999.
- Turnaround: CA team contacts within two to four hours.
- Keep response under 25 words (maximum 2 sentences). No markdown or bullet points.
"""

    reply = ""
    if gemini_client:
        try:
            chat_context = f"{sys_instruction}\n\nRecent Turns:\n"
            for turn in payload.history[-4:]:
                chat_context += f"{turn.role.capitalize()}: {turn.content}\n"
            chat_context += f"Client: {user_msg}\nConsultant:"

            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=chat_context
            )
            reply = response.text.strip().replace("*", "").replace("#", "")
        except Exception as e:
            print(f"Gemini API Error: {e}")

    if not reply:
        if is_closing:
            reply = "बहुत-बहुत धन्यवाद! हमारे सीए पार्टनर दो से चार घंटे में आपसे संपर्क करेंगे। आपका दिन शुभ हो।"
        else:
            reply = "आपकी सैलरी, रेंटल इनकम और स्टॉक लाभ के लिए फॉर्म ITR-2 लागू है। हमारी फीस ₹2,999 है और सीए टीम दो से चार घंटे में आपसे संपर्क करेगी।"

    reply = normalize_spoken_text(reply, lang_code)

    return {
        "reply": reply,
        "session_state": state,
        "call_ended": is_closing
    }

@app.get("/api/tax/download-memo-pdf")
async def download_memo_pdf(client_name: str = "Client", income: float = 1500000.0):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 20mm; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; margin: 0; padding: 0; }}
            .header {{ border-bottom: 2px solid #2563eb; padding-bottom: 12px; margin-bottom: 24px; }}
            .firm-title {{ font-size: 22px; font-weight: bold; color: #1e3a8a; }}
            .firm-sub {{ font-size: 11px; color: #64748b; margin-top: 4px; }}
            .memo-title {{ font-size: 16px; font-weight: bold; color: #0f172a; margin: 20px 0 10px; background: #f1f5f9; padding: 8px 12px; border-left: 4px solid #2563eb; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 12px; }}
            th, td {{ padding: 10px; border: 1px solid #cbd5e1; text-align: left; }}
            th {{ background: #f8fafc; font-weight: bold; color: #334155; }}
            .total-row {{ font-weight: bold; background: #f1f5f9; }}
            .footer {{ margin-top: 40px; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="firm-title">KSP CONSULTING & SOLUTIONS</div>
            <div class="firm-sub">Professional Tax Advisory, Compliance & Regulatory Filing | Hyderabad, India</div>
        </div>

        <div class="memo-title">STATUTORY TAX CONSULTATION & FILING INTAKE MEMO</div>
        
        <p style="font-size: 12px; color: #475569;">
            <strong>Assessment Year:</strong> 2026-27 | <strong>Financial Year:</strong> 2025-26<br>
            <strong>Client Reference:</strong> {client_name} | <strong>Status:</strong> Intake Finalized
        </p>

        <table>
            <tr>
                <th style="width: 35%;">Parameter</th>
                <th>Assessment Findings</th>
            </tr>
            <tr>
                <td>Reported Income Sources</td>
                <td>Salary Income, Income from House Property (Rental), Equity/Capital Gains</td>
            </tr>
            <tr>
                <td>Statutory ITR Form</td>
                <td><strong>Form ITR-2</strong> (Required for Capital Gains and Multi-source Income)</td>
            </tr>
            <tr>
                <td>Tax Regime Assessment</td>
                <td>Section 115BAC (New Tax Regime with Standard Deduction benefit)</td>
            </tr>
            <tr>
                <td>Professional Filing Fee</td>
                <td><strong>INR 2,999/-</strong> (Inclusive of computation and verification)</td>
            </tr>
            <tr class="total-row">
                <td>CA Review Timeline (SLA)</td>
                <td>Within 2 to 4 Business Hours</td>
            </tr>
        </table>

        <div class="footer">
            <p><strong>Verification Notice:</strong> This summary is generated autonomously by KSP Consulting Tax Infrastructure. A Chartered Accountant will review all source documents prior to final submission on the Income Tax e-filing portal.</p>
        </div>
    </body>
    </html>
    """
    
    # PDF generation using WeasyPrint or fallback
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=KSP_Tax_Assessment_{client_name}.pdf"
        })
    except Exception:
        # Fallback to HTML-printable view if weasyprint library has dependencies
        return HTMLResponse(content=html_content)

# --- REVERSE PROXY MOUNT FOR STREAMLIT ---
import httpx
from fastapi.responses import StreamingResponse

STREAMLIT_INTERNAL_URL = "http://127.0.0.1:8501"

@app.api_route("/portal/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_streamlit(request: Request, path: str = ""):
    target_url = f"{STREAMLIT_INTERNAL_URL}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(base_url=STREAMLIT_INTERNAL_URL, timeout=60.0) as client:
        body = await request.body()
        req = client.build_request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.query_params,
            content=body
        )
        res = await client.send(req, stream=True)
        return StreamingResponse(
            res.aiter_raw(),
            status_code=res.status_code,
            headers=dict(res.headers),
            background=None
        )
