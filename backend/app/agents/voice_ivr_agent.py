import os
import re
from typing import List, Dict, Any

class GeminiVoiceIVRAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self.api_key:
                return None
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")
                return None
        return self._client

    def _format_for_telephony_tts(self, text: str) -> str:
        """
        Formats statutory acronyms with hyphens and spaces so browser
        text-to-speech synthesizers pronounce them clearly without slurring.
        """
        # Format Section 44ADA / 44AB
        text = re.sub(r'44ADA', '44 A-D-A', text, flags=re.IGNORECASE)
        text = re.sub(r'44AB', '44 A-B', text, flags=re.IGNORECASE)
        text = re.sub(r'44AA', '44 A-A', text, flags=re.IGNORECASE)
        text = re.sub(r'115BAC', '115 B-A-C', text, flags=re.IGNORECASE)
        
        # Format ITR forms
        text = re.sub(r'\bITR-(\d)\b', r'I-T-R \1', text, flags=re.IGNORECASE)
        text = re.sub(r'\bITR(\d)\b', r'I-T-R \1', text, flags=re.IGNORECASE)
        
        # Remove markdown asterisks or hash symbols that TTS engines read out loud
        text = text.replace('*', '').replace('#', '').replace('_', '')
        return text.strip()

    def generate_ivr_turn(self, conversation_history: List[Dict[str, str]], user_input: str) -> str:
        # Check hangup intent immediately
        hangup_words = ["bye", "goodbye", "disconnect", "end call", "cut call", "no thanks", "nothing else"]
        user_lower = user_input.lower().strip()
        if any(w in user_lower for w in ["bye", "goodbye", "cut the call", "end the call"]):
            return "Thank you for contacting KSP Consulting. Have a wonderful day ahead. Goodbye. [CALL_ENDED]"

        if not self.client:
            return (
                "Welcome to KSP Consulting. Our AI voice desk is currently undergoing maintenance. "
                "Please reach our advisory desk directly at support@kspconsulting.in."
            )

        system_instruction = (
            "You are the autonomous voice tax intake agent for KSP Consulting & Solutions in India. "
            "Follow these strict telephony speaking rules:\n"
            "1. BREVITY: Keep every turn under 35 words (1 or 2 crisp sentences only). "
            "Never generate paragraphs or bullet points; long text will be cut off by the browser audio buffer.\n"
            "2. PRONUNCIATION: Always write statutory references as 'Section 44 A-D-A', 'Section 44 A-B', "
            "'I-T-R 1', 'I-T-R 2', 'I-T-R 3', or 'I-T-R 4'.\n"
            "3. STATUTORY LOGIC: "
            "- Freelancers under ₹75 Lakhs without stock trading -> Section 44 A-D-A via I-T-R 4.\n"
            "- Salaried with capital gains/stocks -> I-T-R 2.\n"
            "- Freelance + Stock capital gains -> I-T-R 3 (cannot use I-T-R 4).\n"
            "4. EMAIL/LEAD CAPTURE: Confirm name, email, and phone number succinctly. "
            "If an email sounds phonetically distorted, confirm it once gently.\n"
            "5. CALL CONCLUSION: When the user confirms all details, conclude with: "
            "'Thank you for choosing KSP Consulting. Have a wonderful day ahead. Goodbye. [CALL_ENDED]'"
        )

        try:
            contents = [f"System: {system_instruction}"]
            for turn in conversation_history[-6:]:  # Keep recent context window for high response speed
                role = "User" if turn.get("role") == "user" else "Assistant"
                contents.append(f"{role}: {turn.get('content')}")
            contents.append(f"User: {user_input}")

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents="\n".join(contents),
            )
            raw_text = response.text.strip()
            return self._format_for_telephony_tts(raw_text)
        except Exception as e:
            return f"I had trouble hearing that clearly. Could you please repeat your tax question?"