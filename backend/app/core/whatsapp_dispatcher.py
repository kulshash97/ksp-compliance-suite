import os
import httpx
from typing import Optional, Dict, Any

WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages" if PHONE_NUMBER_ID else ""

class WhatsAppDispatcher:
    """
    Automated WhatsApp Lead Dispatcher for KSP Consulting.
    Dispatches computation summaries, ITR forms, and booking confirmations.
    """

    @staticmethod
    async def dispatch_intake_confirmation(
        recipient_phone: str,
        assessee_name: str,
        recommended_form: str,
        taxable_profit: Optional[str] = None,
        refund_due: Optional[str] = None
    ) -> Dict[str, Any]:
        # Normalize Indian phone numbers
        phone = recipient_phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            if len(phone) == 10:
                phone = f"+91{phone}"
            elif phone.startswith("91") and len(phone) == 12:
                phone = f"+{phone}"

        clean_number = phone.replace("+", "")

        message_body = (
            f"⚖️ *KSP Consulting & Solutions — Tax Assessment Summary*\n\n"
            f"Hello *{assessee_name}*,\n\n"
            f"Thank you for contacting our Autonomous Tax Intake Desk. Here is your preliminary assessment:\n"
            f"• *Recommended Form:* {recommended_form}\n"
        )
        if taxable_profit:
            message_body += f"• *Presumptive Income:* Rs. {taxable_profit}\n"
        if refund_due:
            message_body += f"• *Estimated Net Refund:* Rs. {refund_due}\n"

        message_body += (
            f"\nYour digital computation pack is queued for statutory review. "
            f"A certified consultant will connect with you shortly.\n\n"
            f"_KSP Consulting & Solutions | AY 2026-27_"
        )

        if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
            print(f"[WhatsApp Local/Sandbox Dispatch] To: {clean_number}\n{message_body}")
            return {
                "status": "queued_local_sandbox",
                "phone": clean_number,
                "preview_body": message_body
            }

        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "text",
            "text": {"body": message_body}
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(WHATSAPP_API_URL, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    return {"status": "dispatched", "response": resp.json()}
                else:
                    return {"status": "failed", "code": resp.status_code, "error": resp.text}
            except Exception as e:
                return {"status": "error", "message": str(e)}
