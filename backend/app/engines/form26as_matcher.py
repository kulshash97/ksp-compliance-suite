import re
from decimal import Decimal
from typing import Dict, Any, List
from pydantic import BaseModel

class ChallanRecord(BaseModel):
    bsr_code: str
    challan_no: str
    deposit_date: str
    amount: Decimal

class Form26ASSummary(BaseModel):
    pan: str
    financial_year: str
    total_tds: Decimal
    total_tcs: Decimal
    total_advance_tax: Decimal
    challans: List[ChallanRecord]

class Form26ASParser:
    def parse(self, text: str) -> Form26ASSummary:
        pan = ""
        m_pan = re.search(r"([A-Z]{5}[0-9]{4}[A-Z]{1})", text)
        if m_pan:
            pan = m_pan.group(1)
            
        fy = "2024-25"
        m_fy = re.search(r"Financial\s+Year\s*[:\-]?\s*(\d{4}\s*[-–]\s*\d{2,4})", text, re.IGNORECASE)
        if m_fy:
            fy = m_fy.group(1)

        # Extract TDS amounts
        tds_matches = re.findall(r"Total\s+Tax\s+Deducted.*?([\d,]+\.\d{2})", text, re.IGNORECASE)
        tds_val = Decimal("0.00")
        if tds_matches:
            tds_val = Decimal(tds_matches[-1].replace(",", ""))
            
        # Extract Challans (Part C of 26AS)
        challans = []
        adv_tax = Decimal("0.00")
        challan_rows = re.findall(r"(\d{7})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+([\d,]+\.\d{2})", text)
        for bsr, d_date, c_no, amt in challan_rows:
            clean_amt = Decimal(amt.replace(",", ""))
            challans.append(ChallanRecord(
                bsr_code=bsr,
                challan_no=c_no,
                deposit_date=d_date,
                amount=clean_amt
            ))
            adv_tax += clean_amt

        return Form26ASSummary(
            pan=pan,
            financial_year=fy,
            total_tds=tds_val,
            total_tcs=Decimal("0.00"),
            total_advance_tax=adv_tax,
            challans=challans
        )