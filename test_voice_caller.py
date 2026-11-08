import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pyttsx3
import speech_recognition as sr
from backend.app.agents.voice_ivr_agent import GeminiVoiceIVRAgent

# Setup Text-to-Speech Engine
tts = pyttsx3.init()
tts.setProperty('rate', 170)  # Telephony conversational cadence

def speak(text: str):
    print(f"\n🤖 KSP Agent: {text}\n")
    tts.say(text)
    tts.runAndWait()
    # Mute buffer to prevent laptop mic from catching trailing speaker reverb
    time.sleep(0.4)

agent = GeminiVoiceIVRAgent()
recognizer = sr.Recognizer()

# Telephony VAD Optimization:
recognizer.pause_threshold = 1.2         # Waits 1.2s of silence before assuming you stopped talking
recognizer.non_speaking_duration = 0.5   # Buffer around voice bursts
recognizer.dynamic_energy_threshold = True

history = []

print("=" * 65)
print("📞 LIVE CALL SIMULATOR (DYNAMIC VAD) — KSP CONSULTING & SOLUTIONS")
print("Press Ctrl+C or say 'hang up' to end the call")
print("=" * 65)

# One-time ambient calibration before starting the call
with sr.Microphone() as source:
    print("Calibrating room audio... (1 sec)")
    recognizer.adjust_for_ambient_noise(source, duration=1.0)

# IVR Opening Greeting
speak("Welcome to KSP Consulting and Solutions. How can our tax desk assist you today?")

HANGUP_KEYWORDS = ["hang up", "bye", "goodbye", "disconnect", "call disconnect"]

consecutive_silence = 0

while True:
    try:
        with sr.Microphone() as source:
            print("🎙️ Listening (Speak naturally)...")
            # timeout=8: waits up to 8s for speech to start; phrase_time_limit=18: allows long explanations
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=18)

        caller_text = recognizer.recognize_google(audio, language="en-IN")
        if not caller_text or len(caller_text.strip()) <= 1:
            continue

        print(f"👤 You (Caller): {caller_text}")
        consecutive_silence = 0

        # Check for natural hangup requests
        if any(kw in caller_text.lower() for kw in HANGUP_KEYWORDS):
            speak("Thank you for contacting KSP Consulting and Solutions. Have a great day ahead. Goodbye.")
            print("\nCall ended by caller.")
            break

        # Process response through Gemini Voice Agent
        reply = agent.generate_ivr_turn(history, caller_text)
        speak(reply)

        # Record conversation history
        history.append({"role": "user", "content": caller_text})
        history.append({"role": "model", "content": reply})

    except sr.WaitTimeoutError:
        consecutive_silence += 1
        if consecutive_silence >= 2:
            speak("Are you still on the line? Feel free to ask your tax or business question.")
            consecutive_silence = 0
        continue

    except sr.UnknownValueError:
        # Ignore minor background ambient noise without interrupting you
        continue

    except KeyboardInterrupt:
        speak("Call ended. Thank you for calling KSP Consulting.")
        print("\nCall disconnected.")
        break

    except Exception as e:
        print(f"Error during audio processing: {e}")
        break