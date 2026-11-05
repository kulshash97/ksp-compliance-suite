import re
from decimal import Decimal
from typing import List, Tuple, Set
from rapidfuzz import fuzz
from backend.app.models.schemas import (
    StandardInvoice,
    ReconciliationRecord,
    ReconciliationSummary,
    ComplianceStatus
)

def normalize_invoice_no(inv_no: str) -> str:
    """Strips leading zeros and non-alphanumeric chars to align formats."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(inv_no)).upper()
    return cleaned.lstrip("0")

class Rule36ReconciliationEngine:
    """
    Deterministic O(N + M) exact matching with O(K * P) bounded fuzzy resolution
    for Section 16 & Rule 36(4) ITC claims.
    """
    def __init__(self, tolerance_inr: Decimal = Decimal("1.00"), fuzzy_threshold: float = 85.0):
        self.tolerance = tolerance_inr
        self.fuzzy_threshold = fuzzy_threshold

    def run(self, books: List[StandardInvoice], gstr2b: List[StandardInvoice]) -> ReconciliationSummary:
        records: List[ReconciliationRecord] = []
        matched_books_idx: Set[int] = set()
        matched_2b_idx: Set[int] = set()

        # Step 1: O(N) Hash indexing for GSTR-2B
        gstr2b_map = {}
        for idx, inv in enumerate(gstr2b):
            key = (inv.supplier_gstin, normalize_invoice_no(inv.invoice_number))
            gstr2b_map.setdefault(key, []).append(idx)

        # Step 2: O(M) Exact Hash Match against Books
        for b_idx, b_inv in enumerate(books):
            b_norm = normalize_invoice_no(b_inv.invoice_number)
            key = (b_inv.supplier_gstin, b_norm)

            if key in gstr2b_map and gstr2b_map[key]:
                cand_idx = gstr2b_map[key].pop(0)
                g_inv = gstr2b[cand_idx]
                matched_books_idx.add(b_idx)
                matched_2b_idx.add(cand_idx)

                tax_diff = abs(b_inv.total_tax - g_inv.total_tax)
                if tax_diff <= self.tolerance:
                    records.append(ReconciliationRecord(
                        invoice_number=b_inv.invoice_number,
                        supplier_gstin=b_inv.supplier_gstin,
                        status=ComplianceStatus.MATCHED,
                        books_taxable=b_inv.taxable_value,
                        gstr2b_taxable=g_inv.taxable_value,
                        books_tax=b_inv.total_tax,
                        gstr2b_tax=g_inv.total_tax,
                        tax_difference=tax_diff,
                        match_score=1.0,
                        notes="Exact match confirmed."
                    ))
                else:
                    records.append(ReconciliationRecord(
                        invoice_number=b_inv.invoice_number,
                        supplier_gstin=b_inv.supplier_gstin,
                        status=ComplianceStatus.PARTIAL_MATCH,
                        books_taxable=b_inv.taxable_value,
                        gstr2b_taxable=g_inv.taxable_value,
                        books_tax=b_inv.total_tax,
                        gstr2b_tax=g_inv.total_tax,
                        tax_difference=tax_diff,
                        match_score=0.95,
                        notes=f"Tax value mismatch exceeding tolerance limit: Rs {tax_diff}"
                    ))

        # Step 3: Fuzzy recovery on unallocated records (Prefixes/Typos)
        unmatched_books = [i for i in range(len(books)) if i not in matched_books_idx]
        unmatched_2b = [j for j in range(len(gstr2b)) if j not in matched_2b_idx]

        for b_idx in list(unmatched_books):
            b_inv = books[b_idx]
            b_norm = normalize_invoice_no(b_inv.invoice_number)

            best_sim = 0.0
            best_match_j = None

            for g_idx in unmatched_2b:
                g_inv = gstr2b[g_idx]
                if b_inv.supplier_gstin != g_inv.supplier_gstin:
                    continue

                g_norm = normalize_invoice_no(g_inv.invoice_number)
                sim = fuzz.token_sort_ratio(b_norm, g_norm)

                if sim > best_sim and sim >= self.fuzzy_threshold:
                    best_sim = sim
                    best_match_j = g_idx

            if best_match_j is not None:
                g_inv = gstr2b[best_match_j]
                matched_books_idx.add(b_idx)
                matched_2b_idx.add(best_match_j)
                unmatched_2b.remove(best_match_j)

                tax_diff = abs(b_inv.total_tax - g_inv.total_tax)
                records.append(ReconciliationRecord(
                    invoice_number=f"{b_inv.invoice_number} ~ {g_inv.invoice_number}",
                    supplier_gstin=b_inv.supplier_gstin,
                    status=ComplianceStatus.PARTIAL_MATCH,
                    books_taxable=b_inv.taxable_value,
                    gstr2b_taxable=g_inv.taxable_value,
                    books_tax=b_inv.total_tax,
                    gstr2b_tax=g_inv.total_tax,
                    tax_difference=tax_diff,
                    match_score=float(best_sim) / 100.0,
                    notes=f"Fuzzy invoice match ({best_sim:.1f}%). Confirm vendor invoice formatting."
                ))

        # Step 4: Missing records
        for b_idx in range(len(books)):
            if b_idx not in matched_books_idx:
                inv = books[b_idx]
                records.append(ReconciliationRecord(
                    invoice_number=inv.invoice_number,
                    supplier_gstin=inv.supplier_gstin,
                    status=ComplianceStatus.MISSING_IN_2B,
                    books_taxable=inv.taxable_value,
                    books_tax=inv.total_tax,
                    notes="ITC ineligible under Rule 36(4): Invoice missing in vendor GSTR-2B."
                ))

        for g_idx in range(len(gstr2b)):
            if g_idx not in matched_2b_idx:
                inv = gstr2b[g_idx]
                records.append(ReconciliationRecord(
                    invoice_number=inv.invoice_number,
                    supplier_gstin=inv.supplier_gstin,
                    status=ComplianceStatus.MISSING_IN_BOOKS,
                    gstr2b_taxable=inv.taxable_value,
                    gstr2b_tax=inv.total_tax,
                    notes="Present in GSTR-2B but missing from purchase ledger books."
                ))

        # Summaries
        matched_cnt = sum(1 for r in records if r.status == ComplianceStatus.MATCHED)
        partial_cnt = sum(1 for r in records if r.status == ComplianceStatus.PARTIAL_MATCH)
        missing_2b_cnt = sum(1 for r in records if r.status == ComplianceStatus.MISSING_IN_2B)
        missing_books_cnt = sum(1 for r in records if r.status == ComplianceStatus.MISSING_IN_BOOKS)

        eligible_itc = sum((r.books_tax or Decimal("0.00")) for r in records if r.status == ComplianceStatus.MATCHED)
        pending_itc = sum((r.books_tax or Decimal("0.00")) for r in records if r.status in [ComplianceStatus.PARTIAL_MATCH, ComplianceStatus.MISSING_IN_2B])

        return ReconciliationSummary(
            total_books_records=len(books),
            total_2b_records=len(gstr2b),
            matched_count=matched_cnt,
            partial_match_count=partial_cnt,
            missing_in_books_count=missing_books_cnt,
            missing_in_2b_count=missing_2b_cnt,
            eligible_itc=eligible_itc,
            ineligible_or_pending_itc=pending_itc,
            discrepancies=[r for r in records if r.status != ComplianceStatus.MATCHED]
        )
