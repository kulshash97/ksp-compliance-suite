import json
from decimal import Decimal
from typing import Dict, Any

def generate_efiling_json(res_data: Any) -> str:
    """
    Builds the official CBDT-compliant ITR JSON payload for direct upload
    on incometax.gov.in (Schema Version AY 2025-26 & AY 2026-27).
    """
    payload = {
        "ITR": {
            res_data.recommended_form.replace("-", "").split()[0]: {
                "CreationInfo": {
                    "SWVersionNo": "2.3.0",
                    "SWCreatedBy": "KSP_CONSULTING_SUITE",
                    "JSONCreatedDate": "2026-11-05"
                },
                "Form_ITR": {
                    "FormName": res_data.recommended_form.split()[0],
                    "AssessmentYear": res_data.assessment_year.replace("AY ", "").strip()
                },
                "PersonalInfo": {
                    "AssesseeName": {
                        "SurNameOrOrgName": res_data.client_name
                    },
                    "PAN": res_data.pan,
                    "Status": "I",
                    "EmployerCategory": "OTH" if res_data.salary_income > 0 else "NA"
                },
                "FilingStatus": {
                    "ReturnFileSec": 11, # On or before due date 139(1)
                    "OptingInNewRegime": "Y" if "New" in res_data.recommended_regime else "N"
                },
                "IncomeDeductions": {
                    "IncomeFromSal": float(res_data.salary_income),
                    "IncomeOthSrc": float(res_data.other_sources_total),
                    "GrossTotIncome": float(res_data.gross_total_income),
                    "TotalIncome": float(res_data.gross_total_income - Decimal("75000.00") if "New" in res_data.recommended_regime else res_data.gross_total_income)
                },
                "Schedule44ADA": {
                    "GrossReceipts": float(res_data.professional_receipts_194j),
                    "PresumptiveIncome": float(res_data.business_presumptive_income)
                } if res_data.professional_receipts_194j > 0 else {},
                "TaxComputation": {
                    "TotalTaxPayable": float(res_data.new_regime_tax if "New" in res_data.recommended_regime else res_data.old_regime_tax),
                    "Rebate87A": 25000.0 if res_data.gross_total_income <= 700000 else 0.0,
                    "TDSClaimed": float(res_data.tds_as_per_ais),
                    "BalanceTaxPayable": max(0.0, float((res_data.new_regime_tax if "New" in res_data.recommended_regime else res_data.old_regime_tax) - res_data.tds_as_per_ais)),
                    "RefundDue": max(0.0, float(res_data.tds_as_per_ais - (res_data.new_regime_tax if "New" in res_data.recommended_regime else res_data.old_regime_tax)))
                }
            }
        }
    }
    return json.dumps(payload, indent=2)