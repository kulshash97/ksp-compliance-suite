from decimal import Decimal
from typing import Dict, Any, List
from pydantic import BaseModel

class SalesMismatchResult(BaseModel):
    gstr1_turnover: Decimal
    gstr3b_turnover: Decimal
    gstr1_tax: Decimal
    gstr3b_tax: Decimal
    tax_difference: Decimal
    rule_88c_breach: bool
    status: str
    remediation_note: str

class GSTSalesReconciliationEngine:
    @staticmethod
    def reconcile(
        gstr1_turnover: Decimal,
        gstr1_tax: Decimal,
        gstr3b_turnover: Decimal,
        gstr3b_tax: Decimal
    ) -> SalesMismatchResult:
        """
        Rule 88C: If tax liability in GSTR-1 exceeds GSTR-3B by more than
        a specified percentage (standard benchmark > 10% and Rs 25,000),
        system raises Form DRC-01B statutory notice risk.
        """
        diff = gstr1_tax - gstr3b_tax
        breach = False
        status = "COMPLIANT"
        remediation = "Outward liability matches within tolerance."

        if diff > Decimal("25000.00") and (gstr3b_tax == 0 or (diff / gstr1_tax) > Decimal("0.10")):
            breach = True
            status = "DRC-01B RISK"
            remediation = f"Warning: GSTR-1 exceeds GSTR-3B by Rs {diff:,.2f}. Taxpayer is liable for automated DRC-01B notice under Rule 88C."
        elif diff < Decimal("0.00"):
            status = "EXCESS TAX PAID"
            remediation = f"Tax paid in GSTR-3B exceeds GSTR-1 by Rs {abs(diff):,.2f}. Claim adjustment in subsequent periods."

        return SalesMismatchResult(
            gstr1_turnover=gstr1_turnover,
            gstr3b_turnover=gstr3b_turnover,
            gstr1_tax=gstr1_tax,
            gstr3b_tax=gstr3b_tax,
            tax_difference=diff,
            rule_88c_breach=breach,
            status=status,
            remediation_note=remediation
        )