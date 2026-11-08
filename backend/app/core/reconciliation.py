import hashlib
from decimal import Decimal
from typing import List, Dict, Any

def normalize_invoice_num(inv_num: str) -> str:
    return "".join(c for c in str(inv_num).upper() if c.isalnum())

class GSTReconciliationPipeline:
    @staticmethod
    def reconcile(purchase_register: List[Dict[str, Any]], gstr_2b: List[Dict[str, Any]]) -> dict:
        matched_records = []
        missing_in_2b = []
        ineligible_records = []

        total_pr_itc = Decimal('0.00')
        matched_itc = Decimal('0.00')
        unmatched_itc = Decimal('0.00')

        gstr2b_index = {}
        for entry in gstr_2b:
            gstin = str(entry.get("gstin", "")).strip().upper()
            inv = normalize_invoice_num(entry.get("invoice_no", ""))
            key = f"{gstin}#{inv}"
            gstr2b_index[key] = entry

        for pr_row in purchase_register:
            gstin = str(pr_row.get("gstin", "")).strip().upper()
            inv = normalize_invoice_num(pr_row.get("invoice_no", ""))
            key = f"{gstin}#{inv}"

            claimed_itc = Decimal(str(pr_row.get("itc_amount", "0.00")))
            total_pr_itc += claimed_itc

            if key in gstr2b_index:
                two_b_row = gstr2b_index[key]
                is_itc_eligible = two_b_row.get("itc_eligible", True)

                if is_itc_eligible:
                    matched_itc += claimed_itc
                    matched_records.append({
                        "gstin": gstin,
                        "invoice_no": pr_row.get("invoice_no"),
                        "claimed_itc": str(claimed_itc),
                        "status": "MATCHED"
                    })
                else:
                    ineligible_records.append({
                        "gstin": gstin,
                        "invoice_no": pr_row.get("invoice_no"),
                        "claimed_itc": str(claimed_itc),
                        "reason": "VENDOR_TAGGED_INELIGIBLE"
                    })
            else:
                unmatched_itc += claimed_itc
                missing_in_2b.append({
                    "gstin": gstin,
                    "invoice_no": pr_row.get("invoice_no"),
                    "claimed_itc": str(claimed_itc),
                    "status": "NOT_FOUND_IN_2B"
                })

        audit_body = f"{total_pr_itc}:{matched_itc}:{unmatched_itc}:{len(matched_records)}"
        computation_hash = hashlib.sha256(audit_body.encode('utf-8')).hexdigest()

        return {
            "summary": {
                "total_pr_invoices": len(purchase_register),
                "total_2b_invoices": len(gstr_2b),
                "total_claimed_itc": str(total_pr_itc),
                "matched_itc": str(matched_itc),
                "unmatched_itc": str(unmatched_itc),
                "match_rate_pct": float(round((matched_itc / total_pr_itc * 100), 2)) if total_pr_itc > 0 else 100.0,
                "computation_hash": computation_hash
            },
            "matched_invoices": matched_records,
            "missing_in_2b": missing_in_2b,
            "ineligible_records": ineligible_records
        }
