import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.agents.voice_ivr_agent import GeminiVoiceIVRAgent

ivr = GeminiVoiceIVRAgent()
history = []

print("\n" + "=" * 60)
print("GEMINI VOICE IVR SCREENING TEST")
print("=" * 60)

# Turn 1: Professional income screening
caller_query_1 = (
    "Hi, I am a freelance backend engineer based in Bengaluru. "
    "I received ₹18 Lakhs under Section 194J this financial year. "
    "Which ITR form should I file?"
)
print(f"\n👤 Caller: {caller_query_1}\n")

try:
    response_1 = ivr.generate_ivr_turn(history, caller_query_1)
    print(f"🤖 KSP Voice IVR:\n{response_1}\n")

    history.append({"role": "user", "content": caller_query_1})
    history.append({"role": "model", "content": response_1})

    # Turn 2: Follow-up on presumptive taxation expenses
    caller_query_2 = (
        "Can I declare 50% as my income under presumptive taxation without maintaining books?"
    )
    print(f"👤 Caller: {caller_query_2}\n")

    response_2 = ivr.generate_ivr_turn(history, caller_query_2)
    print(f"🤖 KSP Voice IVR:\n{response_2}\n")

    print("=" * 60)
    print("SUCCESS: Voice IVR Multi-Turn Dialogue Verified ✅")
    print("=" * 60 + "\n")

except Exception as e:
    print(f"❌ Error during IVR execution: {str(e)}")