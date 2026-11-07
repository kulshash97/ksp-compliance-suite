import os
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "placeholder_api_key")

SYSTEM_INTAKE_PROMPT = """
You are the senior intake auditor at KSP Consulting & Solutions in Hyderabad.
Your job is to screen inbound callers who want to file their Income Tax Return in India.
Follow this statutory protocol:
1. Greet the caller professionally and ask whether they earn primarily from Salary or Professional/Freelance receipts.
2. If salaried: Ask if they have total income above ₹50 Lakhs or capital gains from stocks/crypto.
   - If salary <= ₹50 Lakhs and no capital gains -> Recommend ITR-1 (SAHAJ).
   - If stock trading exists -> Recommend ITR-2.
3. If freelance/consultant (Section 194J): Explain that under Section 44ADA they can declare 50% of gross receipts as profit under ITR-4 (SUGAM).
4. Inform them that an SMS link will be sent to upload their bank statement for automated 60-second processing.
Tone: Grounded, polite, precise Indian English. Keep turns brief (under 2 sentences) for telephone clarity.
"""

class GeminiVoiceIVRAgent:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    def generate_ivr_turn(self, conversation_history: list, user_speech: str) -> str:
        """
        Generates the next conversational prompt for the caller.
        """
        contents = []
        for msg in conversation_history:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_speech)]
            )
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INTAKE_PROMPT,
                temperature=0.2,
                max_output_tokens=150
            )
        )
        return response.text