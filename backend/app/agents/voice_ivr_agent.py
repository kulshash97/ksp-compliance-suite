import os
from typing import List, Dict, Any
from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """
You are the autonomous Voice IVR Intake Specialist for KSP Consulting & Solutions.
Your goal is to screen Indian taxpayers, freelance professionals, and business founders over a phone call concisely and accurately.

Rules for Voice Phone Responses:
1. Speak in clear, complete conversational sentences. Keep the total answer to 2 or 3 complete sentences so text-to-speech reads smoothly.
2. Provide direct answers: recommend ITR-4 under Section 44ADA for technical/freelance professionals under 75 Lakhs, ITR-1 for salaried/interest, or note statutory audit requirements under Section 44AB.
3. Never use markdown asterisks (*), hashtags, bullets, or emojis because this output is read verbatim by a telephone voice engine.
"""

class GeminiVoiceIVRAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model_name = "gemini-3.8-flash"

    def generate_ivr_turn(self, conversation_history: List[Dict[str, str]], user_input: str) -> str:
        """
        Processes a multi-turn conversation turn and returns a spoken-dialogue response.
        """
        contents = []
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
        
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            max_output_tokens=1000,
            top_p=0.95
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            return f"I apologize, but I encountered an error processing your request: {str(e)}"