import os
import hmac
import hashlib
import time
import jwt
from typing import Dict, Any, Optional
import razorpay

# Production & Sandbox Secret Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholderKey")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "placeholderSecret")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ksp-compliance-secure-jwt-signing-key-2026")
JWT_ALGORITHM = "HS256"

# Pricing Matrix in Paise (INR)
TIER_PRICING = {
    "ITR_INDIVIDUAL": {"amount": 49900, "currency": "INR", "label": "Individual ITR Filing Pack"},
    "CA_FIRM_MONTHLY": {"amount": 249900, "currency": "INR", "label": "CA Firm Unlimited Compliance Pass"}
}

class RazorpayPaymentManager:
    def __init__(self):
        self.client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

    def create_order(self, tier: str, client_email: str, client_phone: str) -> Dict[str, Any]:
        """
        Generates a server-side Razorpay order to guarantee amount integrity.
        """
        if tier not in TIER_PRICING:
            raise ValueError(f"Invalid tier: {tier}")

        tier_info = TIER_PRICING[tier]
        receipt_id = f"rcpt_{int(time.time())}_{tier[:3]}"

        order_data = {
            "amount": tier_info["amount"],
            "currency": tier_info["currency"],
            "receipt": receipt_id,
            "notes": {
                "tier": tier,
                "email": client_email,
                "phone": client_phone,
                "purpose": tier_info["label"]
            }
        }
        order = self.client.order.create(data=order_data)
        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
            "tier": tier
        }

    @staticmethod
    def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """
        Verifies Razorpay HMAC-SHA256 signature to guarantee payment authenticity.
        """
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            key=RAZORPAY_KEY_SECRET.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(generated_signature, razorpay_signature)

    @staticmethod
    def generate_access_token(order_id: str, payment_id: str, tier: str, validity_hours: int = 24) -> str:
        """
        Generates a signed, tamper-proof access token for compliance features.
        """
        expiration = int(time.time()) + (validity_hours * 3600)
        payload = {
            "sub": payment_id,
            "order_id": order_id,
            "tier": tier,
            "exp": expiration,
            "scope": "unlimited" if tier == "CA_FIRM_MONTHLY" else "single_filing"
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def validate_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Validates token integrity and expiry before unlocking exports.
        """
        try:
            decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return decoded
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None