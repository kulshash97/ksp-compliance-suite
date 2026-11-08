import os
import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

app = FastAPI(
    title="KSP Consulting & Solutions Corporate Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None
)

# Cross-Origin Resource Sharing (CORS) for edge browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini Client Initialization
api_key = os.getenv("GEMINI_API_KEY")
gemini_client = None

if api_key:
    try:
        from google import genai
        gemini_client = genai.Client(api_key=api_key)
    except Exception as err:
        print(f"Warning: Failed to initialize Google GenAI client: {err}")


# --- DATA MODELS ---

class TurnMessage(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    user_input: str
    conversation_history: Optional[List[TurnMessage]] = []


# --- SYSTEM INSTRUCTION FOR VOICE & CHAT DESK ---

SYSTEM_INSTRUCTION = """
You are the autonomous voice & chat tax intake specialist for KSP Consulting & Solutions in India.
Follow these strict telephony speaking rules:
1. BREVITY: Keep answers strictly within 1-2 concise sentences (under 30 words total). Never use bullet points, tables, or markdown asterisks.
2. STATUTORY PRONUNCIATION & ROUTING:
   - Always refer to sections with spaces: 'Section 44 A-D-A', 'Section 44 A-B', and forms as 'I-T-R 1', 'I-T-R 2', 'I-T-R 3', or 'I-T-R 4'.
   - Salaried individuals with capital gains from stocks/mutual funds -> Form I-T-R 2.
   - Pure freelancers/professionals earning under ₹75 Lakhs without stock trading -> Section 44 A-D-A via Form I-T-R 4.
   - Freelance earnings combined with stock capital gains or F&O trading -> Form I-T-R 3.
   - Salaried under ₹50 Lakhs with no capital gains -> Form I-T-R 1.
3. INTAKE CAPTURE: Once the applicable form is stated, politely ask for their full name, email, or mobile number.
4. CALL CONCLUSION: When contact details are collected or the user says goodbye, conclude with:
   'Thank you for choosing KSP Consulting. Have a wonderful day ahead. Goodbye.'
"""


# --- ROUTE HANDLERS ---

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "KSP Consulting & Solutions Corporate Gateway",
        "gemini_connected": gemini_client is not None
    }


@app.get("/", response_class=HTMLResponse)
async def serve_landing_page():
    template_path = Path(__file__).resolve().parent / "templates" / "index.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        """
        <html>
            <head><title>KSP Consulting & Solutions</title></head>
            <body style="font-family: sans-serif; background: #0f172a; color: white; padding: 40px; text-align: center;">
                <h2>KSP Consulting & Solutions Gateway is Active</h2>
                <p>Template 'backend/app/templates/index.html' not found. Please upload the template file.</p>
            </body>
        </html>
        """,
        status_code=200
    )


@app.post("/api/voice/chat")
async def handle_intake_turn(payload: ChatPayload):
    user_text = payload.user_input.strip()
    if not user_text:
        return {"reply": "I am listening. How can our tax desk assist you?", "call_ended": False}

    if not gemini_client:
        return {
            "reply": "Welcome to KSP Consulting. Our AI tax desk is initializing. Please contact support@kspconsulting.in.",
            "call_ended": False
        }

    try:
        contents = [f"System: {SYSTEM_INSTRUCTION}"]
        for turn in (payload.conversation_history or [])[-6:]:
            role_tag = "User" if turn.role == "user" else "Assistant"
            contents.append(f"{role_tag}: {turn.content}")
        contents.append(f"User: {user_text}")

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="\n".join(contents),
        )

        reply = response.text.strip().replace("*", "").replace("#", "").replace("`", "")
        is_end = any(phrase in reply.lower() for phrase in ["goodbye", "have a wonderful day ahead", "have a great day"])

        return {
            "reply": reply,
            "call_ended": is_end
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")