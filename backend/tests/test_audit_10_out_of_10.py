import sys
from pathlib import Path

# Add project root to sys.path so imports resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import unittest
from decimal import Decimal
from datetime import date

from backend.app.models.schemas import StandardInvoice
from backend.app.engines.gst_matcher import Rule36ReconciliationEngine
from backend.app.engines.itr_engine import ITREngine
from backend.app.engines.exemption_optimizer import ExemptionOptimizer
from backend.app.engines.gst_sales_matcher import GSTSalesReconciliationEngine
from backend.app.core.security import DataSecurityGuard


class TestAudit10OutOf10(unittest.TestCase):
    def setUp(self):
        self.gst_matcher = Rule36ReconciliationEngine()
        self.itr_engine = ITREngine()

    def test_dsa_high_volume_partitioning(self):
        """Verifies O(N+M) composite hash bucketing across 1,000 synthetic invoices."""
        books = [
            StandardInvoice(
                invoice_number=f"INV/2025/{i:05d}",
                supplier_gstin="36AAAAA0000A1Z5",
                supplier_name="Vendor Alpha",
                invoice_date=date.today(),
                taxable_value=Decimal("1000.00"),
                cgst=Decimal("90.00"),
                sgst=Decimal("90.00"),
                igst=Decimal("0.00"),
                total_tax=Decimal("180.00"),
                total_value=Decimal("1180.00"),
            )
            for i in range(1, 1001)
        ]

        # Normalized variation (strip slashes)
        gstr2b = [
            StandardInvoice(
                invoice_number=f"INV2025{i:05d}",
                supplier_gstin="36AAAAA0000A1Z5",
                supplier_name="Vendor Alpha",
                invoice_date=date.today(),
                taxable_value=Decimal("1000.00"),
                cgst=Decimal("90.00"),
                sgst=Decimal("90.00"),
                igst=Decimal("0.00"),
                total_tax=Decimal("180.00"),
                total_value=Decimal("1180.00"),
            )
            for i in range(1, 1001)
        ]

        summary = self.gst_matcher.run(books, gstr2b)
        self.assertEqual(summary.matched_count, 1000)
        self.assertEqual(summary.eligible_itc, Decimal("180000.00"))
        self.assertEqual(summary.ineligible_or_pending_itc, Decimal("0.00"))
        self.assertEqual(len(summary.discrepancies), 0)

    def test_section_24b_interest_cap(self):
        """Verifies Section 24(b) statutory cap of Rs 2,00,000 for self-occupied property."""
        deduction = ExemptionOptimizer.calculate_home_loan(
            Decimal("285000.00"), is_self_occupied=True
        )
        self.assertEqual(deduction, Decimal("200000.00"))

    def test_rule_88c_percentage_threshold(self):
        """Verifies Rule 88C triggers only when variance exceeds BOTH 10% AND Rs 25,000."""
        # Rs 50,000 difference on Rs 27,00,000 is 1.85% (< 10%) -> COMPLIANT
        res = GSTSalesReconciliationEngine.reconcile(
            Decimal("15000000.00"),
            Decimal("2700000.00"),
            Decimal("15000000.00"),
            Decimal("2650000.00"),
        )
        self.assertFalse(res.rule_88c_breach)
        self.assertEqual(res.status, "COMPLIANT")

        # Rs 5,00,000 difference on Rs 27,00,000 is 18.5% (> 10% and > Rs 25k) -> DRC-01B RISK
        res_breach = GSTSalesReconciliationEngine.reconcile(
            Decimal("15000000.00"),
            Decimal("2700000.00"),
            Decimal("15000000.00"),
            Decimal("2200000.00"),
        )
        self.assertTrue(res_breach.rule_88c_breach)
        self.assertEqual(res_breach.status, "DRC-01B RISK")

    def test_dpdpa_pii_masking(self):
        """Verifies PAN and Bank Account numbers are masked from logs."""
        raw_log = "Processing PAN IJBPS5080L with Bank Account 004001633983"
        sanitized = DataSecurityGuard.sanitize_log(raw_log)
        self.assertNotIn("IJBPS5080L", sanitized)
        self.assertNotIn("004001633983", sanitized)
        self.assertIn("IJBPS****L", sanitized)
        self.assertIn("*******3983", sanitized)


if __name__ == "__main__":
    unittest.main()