from decimal import Decimal, ROUND_HALF_UP
from typing import List
from pydantic import BaseModel

class CMAPeriodProjection(BaseModel):
    year_label: str
    gross_sales: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    operating_expenses: Decimal
    ebitda: Decimal
    depreciation: Decimal
    ebit: Decimal
    interest_term_loan: Decimal
    interest_working_capital: Decimal
    pbt: Decimal
    tax_expense: Decimal
    pat: Decimal
    net_profit_margin_pct: Decimal
    inventory_holding: Decimal
    trade_receivables: Decimal
    other_current_assets: Decimal
    total_current_assets: Decimal
    trade_payables: Decimal
    other_current_liabilities: Decimal
    total_current_liabilities_non_bank: Decimal
    working_capital_gap: Decimal
    margin_money_borrower: Decimal
    max_permissible_bank_finance: Decimal
    current_ratio: Decimal
    dscr: Decimal
    interest_coverage_ratio: Decimal

class CMAEngine:
    def __init__(self, tax_rate: Decimal = Decimal("0.25")):
        self.tax_rate = tax_rate

    def project_5_years(
        self,
        base_revenue: Decimal,
        annual_growth_rates: List[Decimal],
        cogs_pct: Decimal = Decimal("0.68"),
        opex_pct: Decimal = Decimal("0.09"),
        debtor_days: int = 45,
        inventory_days: int = 60,
        creditor_days: int = 30,
        term_loan_principal: Decimal = Decimal("2500000.00"),
        term_loan_interest_rate: Decimal = Decimal("0.105"),
        tenure_years: int = 5
    ) -> List[CMAPeriodProjection]:
        projections = []
        current_sales = base_revenue
        remaining_loan = term_loan_principal
        annual_principal = term_loan_principal / Decimal(str(tenure_years))

        for idx, growth in enumerate(annual_growth_rates):
            year_num = idx + 1
            year_val = 26 + year_num
            label = f"FY{year_val} (P)"
            
            current_sales = (current_sales * (Decimal("1.00") + growth)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            cogs = (current_sales * cogs_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gp = current_sales - cogs
            gp_margin = ((gp / current_sales) * Decimal("100.00")).quantize(Decimal("0.01"))
            opex = (current_sales * opex_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ebitda = gp - opex
            depreciation = (current_sales * Decimal("0.025")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ebit = ebitda - depreciation
            term_interest = (remaining_loan * term_loan_interest_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            wc_interest = (current_sales * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            tot_interest = term_interest + wc_interest
            pbt = ebit - tot_interest
            tax = (pbt * self.tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if pbt > 0 else Decimal("0.00")
            pat = pbt - tax
            npm = ((pat / current_sales) * Decimal("100.00")).quantize(Decimal("0.01"))

            debtors = ((current_sales / Decimal("365")) * Decimal(str(debtor_days))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            inventory = ((cogs / Decimal("365")) * Decimal(str(inventory_days))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            other_ca = (current_sales * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_ca = debtors + inventory + other_ca

            creditors = ((cogs / Decimal("365")) * Decimal(str(creditor_days))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            other_cl = (current_sales * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_cl = creditors + other_cl

            wcg = total_ca - total_cl
            margin = (total_ca * Decimal("0.25")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            mpbf = max(Decimal("0.00"), wcg - margin)

            cur_liab = total_cl + mpbf
            cr = (total_ca / cur_liab).quantize(Decimal("0.02")) if cur_liab > 0 else Decimal("1.33")
            dscr_num = pat + depreciation + term_interest
            dscr_den = annual_principal + term_interest
            dscr = (dscr_num / dscr_den).quantize(Decimal("0.02")) if dscr_den > 0 else Decimal("2.00")
            ic = (ebit / tot_interest).quantize(Decimal("0.02")) if tot_interest > 0 else Decimal("5.00")

            remaining_loan = max(Decimal("0.00"), remaining_loan - annual_principal)

            projections.append(CMAPeriodProjection(
                year_label=label, gross_sales=current_sales, cogs=cogs, gross_profit=gp,
                gross_margin_pct=gp_margin, operating_expenses=opex, ebitda=ebitda,
                depreciation=depreciation, ebit=ebit, interest_term_loan=term_interest,
                interest_working_capital=wc_interest, pbt=pbt, tax_expense=tax, pat=pat,
                net_profit_margin_pct=npm, inventory_holding=inventory, trade_receivables=debtors,
                other_current_assets=other_ca, total_current_assets=total_ca,
                trade_payables=creditors, other_current_liabilities=other_cl,
                total_current_liabilities_non_bank=total_cl, working_capital_gap=wcg,
                margin_money_borrower=margin, max_permissible_bank_finance=mpbf,
                current_ratio=cr, dscr=dscr, interest_coverage_ratio=ic
            ))
        return projections