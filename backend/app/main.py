from fastapi import Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from backend.app.agents.voice_ivr_agent import GeminiVoiceIVRAgent

# Initialize the IVR agent
voice_agent = GeminiVoiceIVRAgent()

# In-memory session store for call history (keyed by CallSid)
call_sessions = {}

@app.post("/voice/incoming")
async def voice_incoming(request: Request):
    """
    Triggered when a caller dials the Twilio phone number.
    Picks up the call and plays the initial Indian English greeting.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "default")
    
    # Initialize caller history
    call_sessions[call_sid] = []

    response = VoiceResponse()
    
    # Gather speech input from the caller
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
    
    # Fallback if no speech is detected
    response.redirect("/voice/incoming")

    return Response(content=str(response), media_type="application/xml")


@app.post("/voice/process")
async def voice_process(request: Request):
    """
    Processes spoken input from the caller, runs it through Gemini 3.8 Flash,
    and speaks the answer back using Polly.Aditi.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "default")
    caller_speech = form_data.get("SpeechResult", "").strip()

    history = call_sessions.get(call_sid, [])
    response = VoiceResponse()

    # Detect caller hangup intent
    hangup_triggers = ["bye", "hang up", "disconnect", "thank you bye", "goodbye"]
    if any(trigger in caller_speech.lower() for trigger in hangup_triggers):
        response.say(
            "Thank you for contacting KSP Consulting and Solutions. Have a great day ahead. Goodbye.",
            voice="Polly.Aditi",
            language="en-IN"
        )
        response.hangup()
        if call_sid in call_sessions:
            del call_sessions[call_sid]
        return Response(content=str(response), media_type="application/xml")

    # If caller was silent or unclear
    if not caller_speech:
        gather = Gather(
            input="speech",
            action="/voice/process",
            method="POST",
            speech_timeout="auto",
            language="en-IN"
        )
        gather.say(
            "I could not clearly catch that. Could you please state your tax question again?",
            voice="Polly.Aditi",
            language="en-IN"
        )
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")

    # Query Gemini Voice Agent
    agent_reply = voice_agent.generate_ivr_turn(history, caller_speech)

    # Save turn history
    history.append({"role": "user", "content": caller_speech})
    history.append({"role": "model", "content": agent_reply})
    call_sessions[call_sid] = history

    # Gather next turn
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