from decimal import Decimal
from typing import Tuple
from backend.app.models.schemas import EntityType, AuditWorkflowStatus

class StatutoryAuditGatekeeper:
    TURNOVER_CASH_LIMIT = Decimal("10000000.00")       # ₹1 Crore (Section 44AB threshold if cash > 5%)
    TURNOVER_DIGITAL_LIMIT = Decimal("100000000.00")    # ₹10 Crore (Section 44AB threshold if digital >= 95%)
    PRESUMPTIVE_44AD_LIMIT = Decimal("30000000.00")    # ₹3 Crore (Section 44AD presumptive limit)

    def evaluate(
        self,
        entity_type: EntityType,
        annual_turnover: Decimal,
        is_95_percent_digital: bool = True
    ) -> Tuple[AuditWorkflowStatus, str]:
        """
        Evaluates legal structure and gross turnover against statutory Income Tax thresholds.
        Returns:
            - AuditWorkflowStatus: NEEDS_CA_AUDIT, SELF_SERVE, or NO_AUDIT_REQUIRED
            - str: Formal explanatory statutory memo / escrow action note
        """
        # Companies Act, 2013: All Private/Public Limited companies require mandatory statutory CA audit
        if entity_type in (EntityType.PVT_LTD, EntityType.PUBLIC_LTD):
            return (
                AuditWorkflowStatus.NEEDS_CA_AUDIT,
                "Mandatory statutory audit required under Section 139 of the Companies Act, 2013 regardless of turnover. Direct digital filing locked without certified audit sign-off."
            )

        threshold = self.TURNOVER_DIGITAL_LIMIT if is_95_percent_digital else self.TURNOVER_CASH_LIMIT

        if annual_turnover > threshold:
            return (
                AuditWorkflowStatus.NEEDS_CA_AUDIT,
                f"Turnover (₹{annual_turnover:,.2f}) exceeds Section 44AB statutory limit of ₹{threshold:,.2f}. Tax Audit Report in Form 3CA/3CB-3CD is mandatory by a practicing Chartered Accountant."
            )

        return (
            AuditWorkflowStatus.SELF_SERVE,
            f"Turnover (₹{annual_turnover:,.2f}) is within the Section 44AB threshold (₹{threshold:,.2f}). The entity qualifies for autonomous self-serve tax return filing."
        )