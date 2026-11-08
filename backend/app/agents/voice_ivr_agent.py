import os
import re
from typing import List, Dict, Any


class GeminiVoiceIVRAgent:
    """
    Autonomous Voice IVR Agent for KSP Consulting & Solutions.
    Engineered with phonetic statutory formatting, strict conversational brevity,
    and automatic call-termination signal handling.
    """

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

    def _clean_spoken_text(self, text: str) -> str:
        """
        Formats acronyms, sections, and removes markdown/internal tags
        so that text-to-speech engines enunciate them clearly without slurring.
        """
        # Strip internal protocol flags completely so TTS never speaks them
        text = text.replace("[CALL_ENDED]", "").replace("CALL_ENDED", "").strip()

        # Phonetic pronunciation spacing for Indian tax provisions
        text = re.sub(r'44ADA', '44 A-D-A', text, flags=re.IGNORECASE)
        text = re.sub(r'44AB', '44 A-B', text, flags=re.IGNORECASE)
        text = re.sub(r'44AA', '44 A-A', text, flags=re.IGNORECASE)
        text = re.sub(r'115BAC', '115 B-A-C', text, flags=re.IGNORECASE)
        text = re.sub(r'\bITR-(\d)\b', r'I-T-R \1', text, flags=re.IGNORECASE)
        text = re.sub(r'\bITR(\d)\b', r'I-T-R \1', text, flags=re.IGNORECASE)

        # Remove markdown symbols that TTS engines read out loud
        text = text.replace('*', '').replace('#', '').replace('_', '').replace('`', '')
        return text.strip()

    def generate_ivr_turn(self, conversation_history: List[Dict[str, str]], user_input: str) -> dict:
        """
        Executes a voice conversational turn.
        Returns a dict containing:
          - reply: str (cleaned, phonetically formatted response)
          - call_ended: bool (True if the call has reached conclusion)
        """
        user_lower = user_input.lower().strip()
        hangup_words = [
            "bye", "goodbye", "cut call", "end call", "disconnect",
            "no thank you", "no thanks", "nothing else", "that is all"
        ]

        if any(w in user_lower for w in hangup_words):
            return {
                "reply": "Thank you for contacting KSP Consulting. Have a wonderful day ahead. Goodbye.",
                "call_ended": True
            }

        if not self.client:
            return {
                "reply": "Welcome to KSP Consulting. Our AI voice desk is currently initializing. Please contact support@kspconsulting.in.",
                "call_ended": False
            }

        system_instruction = (
            "You are the autonomous voice tax intake agent for KSP Consulting & Solutions in India. "
            "Strict Guidelines:\n"
            "1. MAXIMUM BREVITY: Respond in 1 or 2 concise sentences only (under 30 words). "
            "Never generate long lists or paragraphs; keep it natural for telephony.\n"
            "2. PRONUNCIATION: Refer to forms as 'I-T-R 1', 'I-T-R 2', 'I-T-R 3', 'I-T-R 4', "
            "and sections as 'Section 44 A-D-A' or 'Section 44 A-B'.\n"
            "3. STATUTORY LOGIC:\n"
            "   - Salary + Stock capital gains -> Form I-T-R 2.\n"
            "   - Freelance under ₹75 Lakhs without stock trading -> Section 44 A-D-A via Form I-T-R 4.\n"
            "   - Freelance + Stock capital gains -> Form I-T-R 3 (cannot file I-T-R 4).\n"
            "   - Salaried under ₹50 Lakhs with no capital gains -> Form I-T-R 1.\n"
            "4. LEAD CAPTURE: Gather the taxpayer's name, email, and mobile number efficiently. "
            "If an email sounds distorted, confirm it once gently.\n"
            "5. COMPLETION: When intake is finalized or caller confirms goodbye, conclude with: "
            "'Thank you for choosing KSP Consulting. Goodbye.'"
        )

        try:
            contents = [f"System: {system_instruction}"]
            # Maintain the recent 6 turns for rapid inference speed
            for turn in conversation_history[-6:]:
                role = "User" if turn.get("role") == "user" else "Assistant"
                contents.append(f"{role}: {turn.get('content')}")
            contents.append(f"User: {user_input}")

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents="\n".join(contents),
            )
            raw_text = response.text.strip()
            is_end = "goodbye" in raw_text.lower() or "have a wonderful day" in raw_text.lower()
            clean_reply = self._clean_spoken_text(raw_text)

            return {
                "reply": clean_reply,
                "call_ended": is_end
            }
        except Exception:
            return {
                "reply": "I could not hear that clearly. Could you please repeat your tax question?",
                "call_ended": False
            }