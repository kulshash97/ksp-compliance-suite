import hashlib
from decimal import Decimal, ROUND_HALF_UP

TWOPLACES = Decimal('0.01')

def round_curr(val: Decimal) -> Decimal:
    return val.quantize(TWOPLACES, rounding=ROUND_HALF_UP)

class StatutoryTaxEngine:
    @staticmethod
    def compute_presumptive_44ada(gross_receipts: Decimal) -> dict:
        gross = round_curr(gross_receipts)
        taxable_profit = round_curr(gross * Decimal('0.50'))
        return {
            "gross_receipts": gross,
            "presumptive_profit": taxable_profit,
            "section": "Section 44ADA",
            "eligible": gross <= Decimal('7500000.00')
        }

    @staticmethod
    def compute_115bac_tax(taxable_income: Decimal, standard_deduction: Decimal = Decimal('75000.00')) -> dict:
        taxable = max(Decimal('0.00'), taxable_income - standard_deduction)
        tax = Decimal('0.00')

        if taxable > Decimal('1500000.00'):
            tax += (taxable - Decimal('1500000.00')) * Decimal('0.30')
            taxable = Decimal('1500000.00')
        if taxable > Decimal('1200000.00'):
            tax += (taxable - Decimal('1200000.00')) * Decimal('0.20')
            taxable = Decimal('1200000.00')
        if taxable > Decimal('1000000.00'):
            tax += (taxable - Decimal('1000000.00')) * Decimal('0.15')
            taxable = Decimal('1000000.00')
        if taxable > Decimal('700000.00'):
            tax += (taxable - Decimal('700000.00')) * Decimal('0.10')
            taxable = Decimal('700000.00')
        if taxable > Decimal('300000.00'):
            tax += (taxable - Decimal('300000.00')) * Decimal('0.05')

        if taxable_income - standard_deduction <= Decimal('700000.00'):
            tax = Decimal('0.00')

        cess = round_curr(tax * Decimal('0.04'))
        total_liability = round_curr(tax + cess)

        audit_payload = f"115BAC:{taxable_income}:{standard_deduction}:{total_liability}"
        sha_sig = hashlib.sha256(audit_payload.encode('utf-8')).hexdigest()

        return {
            "taxable_income": taxable_income,
            "standard_deduction": standard_deduction,
            "net_taxable": round_curr(taxable_income - standard_deduction),
            "base_tax": round_curr(tax),
            "health_education_cess": cess,
            "total_tax_payable": total_liability,
            "audit_hash": sha_sig
        }
