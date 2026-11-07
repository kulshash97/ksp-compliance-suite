import re
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from rapidfuzz import fuzz
from backend.app.models.schemas import (
    StandardInvoice,
    ReconciliationRecord,
    ReconciliationStatus,
    ReconciliationSummary
)

class Rule36ReconciliationEngine:
    @staticmethod
    def normalize_invoice_no(inv_no: str) -> str:
        """
        Strips non-alphanumeric noise, slashes, hyphens, and leading zeros.
        Example: 'INV/2024-25/00042' -> 'INV20242542'
        """
        cleaned = re.sub(r"[^A-Za-z0-9]", "", inv_no or "").upper()
        return cleaned.lstrip("0") or "0"

    def run(self, books: List[StandardInvoice], gstr2b: List[StandardInvoice]) -> ReconciliationSummary:
        eligible_itc = Decimal("0.00")
        blocked_itc = Decimal("0.00")
        matched_records: List[ReconciliationRecord] = []
        discrepancies: List[ReconciliationRecord] = []

        # -------------------------------------------------------------
        # 1. HASH INDEXING PHASE: O(M)
        # Partition GSTR-2B invoices by normalized supplier GSTIN.
        # Key: (Normalized_GSTIN) -> List of 2B Invoices
        # Exact Map: (Normalized_GSTIN, Exact_Invoice_No) -> StandardInvoice
        # -------------------------------------------------------------
        gstr2b_bucket: Dict[str, List[StandardInvoice]] = defaultdict(list)
        exact_map: Dict[Tuple[str, str], StandardInvoice] = {}

        for inv in gstr2b:
            norm_gstin = (inv.supplier_gstin or "").strip().upper()
            gstr2b_bucket[norm_gstin].append(inv)
            exact_map[(norm_gstin, (inv.invoice_number or "").strip().upper())] = inv

        matched_2b_ids = set()

        # -------------------------------------------------------------
        # 2. STREAM MATCHING PHASE: O(N)
        # Search space is strictly constrained to identical vendor buckets.
        # -------------------------------------------------------------
        for b_inv in books:
            norm_b_gstin = (b_inv.supplier_gstin or "").strip().upper()
            raw_b_num = (b_inv.invoice_number or "").strip().upper()
            norm_b_num = self.normalize_invoice_no(raw_b_num)

            # --- Tier 1: O(1) Exact Cryptographic Hit ---
            exact_candidate = exact_map.get((norm_b_gstin, raw_b_num))
            if exact_candidate and id(exact_candidate) not in matched_2b_ids:
                tax_diff = abs(b_inv.total_tax - exact_candidate.total_tax)
                if tax_diff <= Decimal("1.00"):
                    eligible_itc += b_inv.total_tax
                    matched_records.append(ReconciliationRecord(
                        status=ReconciliationStatus.EXACT_MATCH,
                        books_invoice=b_inv,
                        gstr2b_invoice=exact_candidate,
                        tax_variance=tax_diff,
                        remarks="Exact cryptographic match"
                    ))
                    matched_2b_ids.add(id(exact_candidate))
                    continue

            # --- Tier 2: Canonical Normalization & Constrained Fuzzy ---
            candidates = gstr2b_bucket.get(norm_b_gstin, [])
            best_match: Optional[StandardInvoice] = None
            best_score = 0.0

            for c_inv in candidates:
                if id(c_inv) in matched_2b_ids:
                    continue
                norm_c_num = self.normalize_invoice_no(c_inv.invoice_number)

                # Check canonical normalized equality (instant)
                if norm_b_num == norm_c_num:
                    best_match = c_inv
                    best_score = 100.0
                    break

                # Constrained Levenshtein within tiny vendor partition
                score = fuzz.ratio(norm_b_num, norm_c_num)
                if score > best_score and score >= 88.0:
                    best_score = score
                    best_match = c_inv

            if best_match:
                tax_diff = abs(b_inv.total_tax - best_match.total_tax)
                if tax_diff <= Decimal("1.00"):
                    eligible_itc += b_inv.total_tax
                    matched_records.append(ReconciliationRecord(
                        status=ReconciliationStatus.FUZZY_MATCH,
                        books_invoice=b_inv,
                        gstr2b_invoice=best_match,
                        tax_variance=tax_diff,
                        remarks=f"Matched with canonical similarity index {best_score:.1f}%"
                    ))
                else:
                    blocked_itc += b_inv.total_tax
                    discrepancies.append(ReconciliationRecord(
                        status=ReconciliationStatus.TAX_MISMATCH,
                        books_invoice=b_inv,
                        gstr2b_invoice=best_match,
                        tax_variance=tax_diff,
                        remarks=f"Tax variance Rs {tax_diff:,.2f} exceeds statutory tolerance (Rs 1.00)"
                    ))
                matched_2b_ids.add(id(best_match))
            else:
                # Invoice missing from GSTR-2B: strictly blocked under Rule 36(4)
                blocked_itc += b_inv.total_tax
                discrepancies.append(ReconciliationRecord(
                    status=ReconciliationStatus.MISSING_IN_2B,
                    books_invoice=b_inv,
                    gstr2b_invoice=None,
                    tax_variance=b_inv.total_tax,
                    remarks="Supplier has not uploaded invoice in GSTR-1. Ineligible under Rule 36(4)."
                ))

        return ReconciliationSummary(
            total_books_records=len(books),
            total_gstr2b_records=len(gstr2b),
            matched_count=len(matched_records),
            mismatched_count=len(discrepancies),
            eligible_itc=eligible_itc,
            ineligible_or_pending_itc=blocked_itc,
            records=matched_records,
            discrepancies=discrepancies
        )