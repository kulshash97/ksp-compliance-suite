from decimal import Decimal
from typing import Tuple
from backend.app.models.schemas import EntityType, AuditWorkflowStatus

class StatutoryAuditGatekeeper:
    """
    Evaluates statutory mandates:
    - Companies Act 2013, Sec 139/141: Mandatory statutory audit for Pvt Ltd & Public Ltd.
    - Income-tax Act 1961, Sec 44AB: Tax audit threshold checks.
    """
    def __init__(self, digital_turnover_threshold: Decimal = Decimal("100000000.00"), cash_turnover_threshold: Decimal = Decimal("10000000.00")):
        self.digital_threshold = digital_turnover_threshold  # Rs 10 Crore (if digital >= 95%)
        self.cash_threshold = digital_turnover_threshold if digital_turnover_threshold < cash_turnover_threshold else cash_turnover_threshold # Rs 1 Crore standard

    def evaluate(self, entity_type: EntityType, annual_turnover: Decimal, is_95_percent_digital: bool = True) -> Tuple[AuditWorkflowStatus, str]:
        # 1. Corporate Entities require mandatory Statutory Audit regardless of turnover
        if entity_type in [EntityType.PVT_LTD, EntityType.PUBLIC_LTD]:
            return (
                AuditWorkflowStatus.NEEDS_CA_AUDIT,
                "Mandatory Statutory Audit required under Section 139 of the Companies Act, 2013. Partner CA sign-off with UDIN mandated."
            )

        # 2. Income Tax Act Sec 44AB threshold check
        effective_limit = self.digital_threshold if is_95_percent_digital else self.cash_threshold

        if annual_turnover > effective_limit:
            limit_display = "Rs 10 Crore (Digital)" if is_95_percent_digital else "Rs 1 Crore (Cash/Standard)"
            return (
                AuditWorkflowStatus.NEEDS_CA_AUDIT,
                f"Turnover of Rs {annual_turnover:,.2f} exceeds Sec 44AB limit of {limit_display}. Tax Audit (Form 3CA/3CB + 3CD) required by Partner CA."
            )

        return (
            AuditWorkflowStatus.SELF_SERVE,
            "Non-audit entity. Standard return preparation and tax filing handled directly by KSP Consulting."
        )
