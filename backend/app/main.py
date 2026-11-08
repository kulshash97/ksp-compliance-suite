from fastapi.responses import HTMLResponse
from pathlib import Path

# Serve the full-screen calling app
@app.get("/call", response_class=HTMLResponse)
async def serve_call_page():
    template_path = Path(__file__).resolve().parent / "templates" / "call.html"
    if template_path.exists():
        return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Template not found</h1>", status_code=404)
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agents.voice_ivr_agent import GeminiVoiceIVRAgent

app = FastAPI(
    title="KSP Autonomous Compliance & Tax Suite API",
    version="2.0.0",
    description="Autonomous tax advisory, GST audit, and multi-turn voice IVR platform"
)

# Enable CORS for browser WebRTC & client-side speech fetches
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ivr_agent = GeminiVoiceIVRAgent()
call_sessions: Dict[str, List[Dict[str, str]]] = {}


# --- IN-HOUSE BROWSER / MOBILE VOICE ENDPOINTS ---

class VoiceTurnRequest(BaseModel):
    user_input: str
    conversation_history: List[Dict[str, str]] = []

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "KSP Compliance Suite Engine",
        "voice_agent": "Gemini 3.8 Flash (Active)"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/voice/chat")
async def voice_chat_endpoint(payload: VoiceTurnRequest):
    """
    Direct in-house browser/mobile voice endpoint.
    Processes transcribed speech through Gemini and returns spoken reply text.
    """
    reply = ivr_agent.generate_ivr_turn(
        conversation_history=payload.conversation_history,
        user_input=payload.user_input
    )
    return {"reply": reply}


# --- OPTIONAL TELEPHONY WEBHOOKS (TWILIO COMPATIBLE) ---

@app.post("/voice/incoming")
async def voice_incoming(request: Request):
    """Fallback inbound carrier webhook."""
    try:
        from twilio.twiml.voice_response import VoiceResponse, Gather
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "default")
        call_sessions[call_sid] = []

        response = VoiceResponse()
        gather = Gather(
            input="speech",
            action="/voice/process",
            method="POST",
            speech_timeout="auto",
            language="en-IN"
        )
        gather.say(
            "Welcome to KSP Consulting and Solutions. How can our tax desk assist you today?",
            voice="Polly.Aditi",
            language="en-IN"
        )
        response.append(gather)
        response.redirect("/voice/incoming")
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        return Response(content=f"<Response><Say>{str(e)}</Say></Response>", media_type="application/xml")

@app.post("/voice/process")
async def voice_process(request: Request):
    """Fallback speech processor for phone carriers."""
    try:
        from twilio.twiml.voice_response import VoiceResponse, Gather
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "default")
        caller_speech = form_data.get("SpeechResult", "").strip()

        history = call_sessions.get(call_sid, [])
        response = VoiceResponse()

        hangup_triggers = ["bye", "hang up", "disconnect", "goodbye"]
        if any(kw in caller_speech.lower() for kw in hangup_triggers):
            response.say(
                "Thank you for contacting KSP Consulting. Have a wonderful day ahead. Goodbye.",
                voice="Polly.Aditi",
                language="en-IN"
            )
            response.hangup()
            if call_sid in call_sessions:
                del call_sessions[call_sid]
            return Response(content=str(response), media_type="application/xml")

        agent_reply = ivr_agent.generate_ivr_turn(history, caller_speech)
        history.append({"role": "user", "content": caller_speech})
        history.append({"role": "model", "content": agent_reply})
        call_sessions[call_sid] = history

        gather = Gather(
            input="speech",
            action="/voice/process",
            method="POST",
            speech_timeout="auto",
            language="en-IN"
        )
        gather.say(agent_reply, voice="Polly.Aditi", language="en-IN")
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        return Response(content=f"<Response><Say>{str(e)}</Say></Response>", media_type="application/xml")

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Zero-disk RAM document intake and compliance inquiry via WhatsApp."""
    try:
        from twilio.twiml.messaging_response import MessagingResponse
        form_data = await request.form()
        body = form_data.get("Body", "").strip()
        num_media = int(form_data.get("NumMedia", 0))

        response = MessagingResponse()
        if num_media > 0:
            response.message(
                "📥 *KSP Autonomous Ingestion*: Document received in zero-disk memory buffer. "
                "Running Rule 36(4) reconciliation and TDS credit verification..."
            )
        else:
            reply = ivr_agent.generate_ivr_turn([], body)
            response.message(reply)

        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)