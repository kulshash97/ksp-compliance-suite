from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
from pydantic import BaseModel

class ExemptionResult(BaseModel):
    hra_exemption: Decimal
    home_loan_interest_deduction: Decimal
    total_deductions_old: Decimal

class ExemptionOptimizer:
    @staticmethod
    def calculate_hra(
        basic_salary: Decimal,
        hra_received: Decimal,
        rent_paid: Decimal,
        is_metro: bool = True
    ) -> Decimal:
        """
        Calculates exempt HRA under Section 10(13A) read with Rule 2A:
        Least of:
        1. Actual HRA received
        2. Rent paid minus 10% of basic salary
        3. 50% of basic salary (metro) or 40% (non-metro)
        """
        if rent_paid <= Decimal("0.00") or hra_received <= Decimal("0.00"):
            return Decimal("0.00")
            
        condition_1 = hra_received
        condition_2 = max(Decimal("0.00"), rent_paid - (basic_salary * Decimal("0.10")))
        condition_3 = basic_salary * (Decimal("0.50") if is_metro else Decimal("0.40"))
        
        return min(condition_1, condition_2, condition_3).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_home_loan(interest_paid: Decimal, is_self_occupied: bool = True) -> Decimal:
        """
        Section 24(b): Capped at Rs 2,00,000 for self-occupied properties.
        """
        if is_self_occupied:
            return min(interest_paid, Decimal("200000.00"))
        return interest_paid