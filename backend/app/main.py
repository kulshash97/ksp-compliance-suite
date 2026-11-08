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


class TurnMessage(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    user_input: str
    conversation_history: Optional[List[TurnMessage]] = []


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
            </body>
        </html>
        """,
        status_code=200
    )


@app.get("/suite", response_class=HTMLResponse)
async def serve_compliance_suite():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>KSP Autonomous Compliance Suite</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0e1117; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow: hidden; }
        .topbar {
          height: 48px;
          background: #0f172a;
          border-bottom: 1px solid #1e293b;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 20px;
          color: #f8fafc;
        }
        .topbar a {
          color: #38bdf8;
          text-decoration: none;
          font-size: 13px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .topbar a:hover { text-decoration: underline; }
        .title { font-size: 14px; font-weight: 700; color: #94a3b8; }
        iframe {
          width: 100vw;
          height: calc(100vh - 48px);
          border: none;
        }
      </style>
    </head>
    <body>
      <div class="topbar">
        <a href="/">← Back to Institutional Overview</a>
        <span class="title">⚖️ KSP Statutory & Tax Engine (AY 2026-27)</span>
      </div>
      <iframe src="/?embed=true" id="suite-frame"></iframe>
      <script>
        // Points to Streamlit instance or internal embedded app
        const currentHost = window.location.hostname;
        const port = window.location.port;
        // If testing on localhost, direct to Streamlit port 8501
        if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
          document.getElementById('suite-frame').src = 'http://' + currentHost + ':8501';
        } else {
          // On Render, if deployed as a unified container
          document.getElementById('suite-frame').src = window.location.protocol + '//' + window.location.host + '/?view=suite';
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


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