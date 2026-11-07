import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.payment_gateway import RazorpayPaymentManager

manager = RazorpayPaymentManager()

# 1. Simulate an authenticated order & payment completion
fake_order_id = "order_test_998877"
fake_payment_id = "pay_test_112233"
tier = "ITR_INDIVIDUAL"

# 2. Issue a signed JWT access token (valid for 24 hours)
token = manager.generate_access_token(
    order_id=fake_order_id,
    payment_id=fake_payment_id,
    tier=tier,
    validity_hours=24
)

print("\n" + "="*60)
print("🔑 GENERATED TEST LICENSE TOKEN:")
print("="*60)
print(token)
print("="*60)

# 3. Validate token decode
decoded = manager.validate_access_token(token)
print(f"Token Verification Status: {'VALID ✅' if decoded else 'INVALID ❌'}")
if decoded:
    print(f"Licensed Tier: {decoded.get('tier')}")
    print(f"Scope: {decoded.get('scope')}")
    print(f"Expires (Unix): {decoded.get('exp')}")
print("="*60 + "\n")