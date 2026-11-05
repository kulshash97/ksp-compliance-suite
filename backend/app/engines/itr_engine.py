import io
import re
import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel
from pypdf import PdfReader

class ITRReconciliationResult(BaseModel):
    client_name: str
    pan: str
    assessment_year: str
    financial_year: str
    recommended_form: str
    salary_income: Decimal
    house_property_income: Decimal
    professional_receipts_194j: Decimal
    stcg: Decimal
    ltcg: Decimal
    property_sale_consideration: Decimal
    business_turnover: Decimal
    business_presumptive_income: Decimal
    savings_interest_bank: Decimal
    savings_interest_ais: Decimal
    fd_interest_ais: Decimal
    dividend_income_ais: Decimal
    other_sources_total: Decimal
    tds_as_per_ais: Decimal
    gross_total_income: Decimal
    
    # Old vs New Regime Details
    old_regime_deductions: Decimal
    old_regime_taxable_income: Decimal
    new_regime_taxable_income: Decimal
    old_regime_tax: Decimal
    new_regime_tax: Decimal
    recommended_regime: str
    tax_savings: Decimal
    
    # Audit Flags
    interest_discrepancy: Decimal
    audit_flags: List[str]
    step_by_step_filing_guide: List[Dict[str, str]]

class ITREngine:
    def __init__(self):
        rules_path = Path(__file__).resolve().parent.parent / "core" / "tax_rules.json"
        if rules_path.exists():
            with open(rules_path, "r") as f:
                self.rules_db = json.load(f)
        else:
            self.rules_db = {}

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes, password: Optional[str] = None) -> Tuple[str, bool]:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if reader.is_encrypted:
            if password:
                decrypted = reader.decrypt(password)
                if decrypted == 0:
                    return "", True
            else:
                return "", True
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text, False

    def parse_bank_statement(self, bank_text: str) -> Dict[str, Any]:
        data = {
            "name": "",
            "savings_interest": Decimal("0.00"),
            "salary_inflow": Decimal("0.00"),
            "salary_months": 0,
            "financial_year": "2024-25",
            "assessment_year": "2025-26"
        }

        # Detect AY/FY
        if re.search(r"2025\s*[-–to]+\s*2026|01-04-2025\s*to\s*31-03-2026", bank_text, re.IGNORECASE):
            data["financial_year"] = "2025-26"
            data["assessment_year"] = "2026-27"
        elif re.search(r"2024\s*[-–to]+\s*2025|01-04-2024\s*to\s*31-03-2025", bank_text, re.IGNORECASE):
            data["financial_year"] = "2024-25"
            data["assessment_year"] = "2025-26"

        # Customer Name
        m_name = re.search(r"(?:MS\.|MR\.|MRS\.)\s*([A-Z\s]{4,35})\n", bank_text)
        if m_name:
            data["name"] = m_name.group(1).strip()

        # Dynamic Interest Parsing
        lines = [l.strip() for l in bank_text.split("\n") if l.strip()]
        INTEREST_REGEX = re.compile(
            r"(?:\bint(?:erest)?\.?\s*(?:pd|paid|credite?d?|cr)\b|\bcredit\s+interest\b|\bby\s+interest\b|\bsb\s+int|\bintrst\s+recvd\b)",
            re.IGNORECASE
        )
        EXCLUSION_REGEX = re.compile(r"\b(?:penal|charge|recovery|revers|debit|fee|tds)\b", re.IGNORECASE)

        for i, line in enumerate(lines):
            if INTEREST_REGEX.search(line):
                cand = line + (" " + lines[i+1] if i + 1 < len(lines) else "")
                if EXCLUSION_REGEX.search(line) and not re.search(r"\b(?:cr|credit|deposit)\b", line, re.IGNORECASE):
                    continue
                tokens = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b", cand)
                amounts = [Decimal(tok.replace(",", "")) for tok in tokens if Decimal(tok.replace(",", "")) > Decimal("0.00")]
                if amounts:
                    data["savings_interest"] += amounts[0]

        # Salary Extraction
        salary_sum = Decimal("0.00")
        sal_count = 0
        for i, line in enumerate(lines):
            if "SALARY" in line.upper():
                window = " ".join(lines[max(0, i-2):min(len(lines), i+5)])
                nums = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b", window)
                for n in nums:
                    val = Decimal(n.replace(",", ""))
                    if Decimal("15000.00") <= val <= Decimal("500000.00"):
                        salary_sum += val
                        sal_count += 1
                        break

        data["salary_inflow"] = salary_sum
        data["salary_months"] = sal_count
        return data

    def parse_ais(self, ais_text: str) -> Dict[str, Any]:
        data = {
            "name": "",
            "pan": "",
            "savings_interest": Decimal("0.00"),
            "fd_interest": Decimal("0.00"),
            "dividend": Decimal("0.00"),
            "receipts_194j": Decimal("0.00"),
            "tds": Decimal("0.00"),
            "property_sale_sft012": Decimal("0.00")
        }

        m_pan = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b", ais_text)
        if m_pan:
            data["pan"] = m_pan.group(1)

        m_name = re.search(r"[A-Z]{5}[0-9]{4}[A-Z]\s+[X\d\s]{10,25}\s+([A-Z\s]{4,40})\n", ais_text)
        if m_name:
            data["name"] = m_name.group(1).strip()

        m_194j = re.search(r"Q\d\([A-Za-z\-]+\)\s+\d{2}/\d{2}/\d{4}\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+Active", ais_text)
        if m_194j:
            data["receipts_194j"] = Decimal(m_194j.group(1).replace(",", ""))
            data["tds"] = Decimal(m_194j.group(2).replace(",", ""))

        m_sft16 = re.search(r"SFT\-016\(SB\).*?(\d+)\s+Active", ais_text, re.DOTALL)
        if m_sft16:
            data["savings_interest"] = Decimal(m_sft16.group(1))

        m_sft12 = re.findall(r"Sale of immovable property \(SFT-012\).*?(\d{1,2},\d{2},\d{3}|\d{6,8})\s+Active", ais_text, re.DOTALL | re.IGNORECASE)
        if m_sft12:
            data["property_sale_sft012"] = Decimal(m_sft12[0].replace(",", ""))

        return data

    def compute(
        self,
        client_name: str,
        pan: str,
        assessment_year: str,
        financial_year: str,
        bank_savings_interest: Decimal,
        ais_savings_interest: Decimal,
        ais_fd_interest: Decimal,
        dividend_income: Decimal,
        professional_194j: Decimal = Decimal("0.00"),
        property_sale_val: Decimal = Decimal("0.00"),
        stcg: Decimal = Decimal("0.00"),
        ltcg: Decimal = Decimal("0.00"),
        salary_income: Decimal = Decimal("0.00"),
        business_turnover: Decimal = Decimal("0.00"),
        tds_paid: Decimal = Decimal("0.00"),
        # Old Regime Deductions
        deduction_80c: Decimal = Decimal("0.00"),
        deduction_80d: Decimal = Decimal("0.00"),
        hra_exemption: Decimal = Decimal("0.00"),
        home_loan_interest_24b: Decimal = Decimal("0.00")
    ) -> ITRReconciliationResult:

        # 1. Rules retrieval for AY
        rules = self.rules_db.get(assessment_year, self.rules_db.get("AY 2025-26", {}))
        std_ded_new = Decimal(str(rules.get("standard_deduction", 75000.0)))
        std_ded_old = Decimal("50000.00")

        # 2. Reconcile interest & business
        effective_savings_int = max(bank_savings_interest, ais_savings_interest)
        interest_diff = abs(bank_savings_interest - ais_savings_interest)
        other_sources = effective_savings_int + ais_fd_interest + dividend_income

        presumptive_prof = (professional_194j * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        presumptive_biz = (business_turnover * Decimal("0.06")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_business = presumptive_prof + presumptive_biz

        gti = salary_income + total_business + stcg + ltcg + other_sources

        # 3. Form Evaluation
        flags = []
        if property_sale_val > 0 or stcg > 0 or ltcg > 0:
            recommended_form = "ITR-3" if total_business > 0 else "ITR-2"
            flags.append(f"Capital Gain / SFT-012 detected (Rs {property_sale_val:,.2f}). Mandates {recommended_form}.")
        elif total_business > 0:
            recommended_form = "ITR-4 (SUGAM)"
        else:
            recommended_form = "ITR-1 (SAHAJ)"

        if interest_diff > 100:
            flags.append(f"Interest Discrepancy of Rs {interest_diff:,.2f} flagged. Bank: Rs {bank_savings_interest:,.2f} | AIS: Rs {ais_savings_interest:,.2f}.")

        # 4. Old Regime Tax Calculation
        capped_80c = min(deduction_80c, Decimal("150000.00"))
        capped_80d = min(deduction_80d, Decimal("100000.00"))
        capped_24b = min(home_loan_interest_24b, Decimal("200000.00"))
        sec_80tta = min(effective_savings_int, Decimal("10000.00"))
        total_old_deductions = (min(salary_income, std_ded_old) + hra_exemption + capped_80c + capped_80d + capped_24b + sec_80tta)

        taxable_old = max(Decimal("0.00"), gti - total_old_deductions)
        old_slabs = rules.get("old_regime_slabs", [])
        old_tax_raw = Decimal("0.00")
        prev_limit = Decimal("0.00")
        for s in old_slabs:
            rate = Decimal(str(s["rate"]))
            up_to = Decimal(str(s["up_to"])) if s["up_to"] is not None else None
            if up_to is not None:
                if taxable_old > prev_limit:
                    taxable_bracket = min(taxable_old, up_to) - prev_limit
                    old_tax_raw += taxable_bracket * rate
                prev_limit = up_to
            else:
                if taxable_old > prev_limit:
                    old_tax_raw += (taxable_old - prev_limit) * rate

        # Rebate 87A Old
        if taxable_old <= Decimal(str(rules.get("rebate_87a_limit_old", 500000.0))):
            old_tax_final = Decimal("0.00")
        else:
            old_tax_final = (old_tax_raw * Decimal("1.04")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 5. New Regime Tax Calculation (Sec 115BAC)
        taxable_new = max(Decimal("0.00"), gti - min(salary_income, std_ded_new))
        new_slabs = rules.get("new_regime_slabs", [])
        new_tax_raw = Decimal("0.00")
        prev_limit_new = Decimal("0.00")
        for s in new_slabs:
            rate = Decimal(str(s["rate"]))
            up_to = Decimal(str(s["up_to"])) if s["up_to"] is not None else None
            if up_to is not None:
                if taxable_new > prev_limit_new:
                    taxable_bracket = min(taxable_new, up_to) - prev_limit_new
                    new_tax_raw += taxable_bracket * rate
                prev_limit_new = up_to
            else:
                if taxable_new > prev_limit_new:
                    new_tax_raw += (taxable_new - prev_limit_new) * rate

        # Rebate 87A New
        if taxable_new <= Decimal(str(rules.get("rebate_87a_limit_new", 1200000.0 if "2026-27" in assessment_year else 700000.0))):
            new_tax_final = Decimal("0.00")
        else:
            new_tax_final = (new_tax_raw * Decimal("1.04")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 6. Regime Verdict
        if new_tax_final <= old_tax_final:
            rec_regime = "New Tax Regime (Section 115BAC)"
            tax_savings = old_tax_final - new_tax_final
        else:
            rec_regime = "Old Tax Regime"
            tax_savings = new_tax_final - old_tax_final

        steps = [
            {"step": "1. Portal Selection", "action": f"Login to e-Filing portal -> Select Assessment Year {assessment_year} -> Choose {recommended_form}."},
            {"step": "2. Gross Income Declaration", "action": f"Declare Gross Salary: Rs {salary_income:,.2f} | Section 44ADA Presumptive: Rs {presumptive_prof:,.2f} | Interest: Rs {other_sources:,.2f}."},
            {"step": "3. Optimal Regime Opt-In", "action": f"Opt for {rec_regime}. Tax savings compared to alternative regime: Rs {tax_savings:,.2f}."},
            {"step": "4. Schedule Taxes Paid", "action": f"Claim verified TDS of Rs {tds_paid:,.2f} from AIS/26AS."},
            {"step": "5. JSON Direct E-Filing", "action": "Download and upload the pre-filled JSON directly to portal for zero-error instant filing."}
        ]

        return ITRReconciliationResult(
            client_name=client_name,
            pan=pan,
            assessment_year=assessment_year,
            financial_year=financial_year,
            recommended_form=recommended_form,
            salary_income=salary_income,
            house_property_income=Decimal("0.00"),
            professional_receipts_194j=professional_194j,
            stcg=stcg,
            ltcg=ltcg,
            property_sale_consideration=property_sale_val,
            business_turnover=business_turnover,
            business_presumptive_income=total_business,
            savings_interest_bank=bank_savings_interest,
            savings_interest_ais=ais_savings_interest,
            fd_interest_ais=Decimal("0.00"),
            dividend_income_ais=Decimal("0.00"),
            other_sources_total=other_sources,
            tds_as_per_ais=tds_paid,
            gross_total_income=gti,
            old_regime_deductions=total_old_deductions,
            old_regime_taxable_income=taxable_old,
            new_regime_taxable_income=taxable_new,
            old_regime_tax=old_tax_final,
            new_regime_tax=new_tax_final,
            recommended_regime=rec_regime,
            tax_savings=tax_savings,
            interest_discrepancy=interest_diff,
            audit_flags=flags,
            step_by_step_filing_guide=steps
        )