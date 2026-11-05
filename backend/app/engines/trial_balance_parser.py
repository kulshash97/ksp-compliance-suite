import io
import re
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Tuple
from pydantic import BaseModel

class ExtractedBaseFinancials(BaseModel):
    base_turnover: Decimal
    cogs: Decimal
    opex: Decimal
    sundry_debtors: Decimal
    closing_inventory: Decimal
    sundry_creditors: Decimal
    
    # Inferred parameters
    cogs_ratio: float
    opex_ratio: float
    debtor_days: int
    inventory_days: int
    creditor_days: int
    unmapped_ledgers_count: int

class TrialBalanceParser:
    """
    Parses unstructured Trial Balance or P&L sheets from Tally, Zoho Books, 
    and Busy Accounting into normalized CMA base-year inputs.
    """
    PATTERNS = {
        "revenue": [r"sales", r"revenue", r"turnover", r"operating income", r"fees received", r"service charges"],
        "cogs": [r"purchase", r"cogs", r"cost of goods", r"direct expense", r"freight inward", r"raw material", r"carriage inward", r"manufacturing"],
        "opex": [r"salary", r"wages", r"rent", r"office", r"admin", r"legal", r"travelling", r"advertising", r"sg&a", r"printing", r"audit fee", r"telephone", r"electricity"],
        "debtors": [r"sundry debtor", r"trade receivable", r"accounts receivable", r"customer balance", r"bills receivable"],
        "inventory": [r"closing stock", r"inventory", r"finished goods", r"work in progress", r"stock-in-hand"],
        "creditors": [r"sundry creditor", r"trade payable", r"accounts payable", r"supplier balance", r"bills payable"]
    }

    def parse(self, file_bytes: bytes, filename: str) -> ExtractedBaseFinancials:
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_bytes), header=None)
            else:
                df = pd.read_excel(io.BytesIO(file_bytes), header=None)
        except Exception as e:
            raise ValueError(f"Failed to read file: {str(e)}")

        # Step 1: Locate header and clean rows
        # Find row containing ledger/account/particulars keywords
        header_row_idx = 0
        for idx, row in df.iterrows():
            row_str = " ".join([str(val).lower() for val in row.values])
            if any(term in row_str for term in ["particular", "ledger", "account", "account name"]):
                header_row_idx = idx
                break

        df = df.iloc[header_row_idx:].reset_index(drop=True)
        # Drop columns that are completely empty
        df = df.dropna(how="all", axis=1)

        # Step 2: Separate text columns (Ledger names) and numeric columns (Balances)
        ledger_col = 0
        for col in df.columns:
            sample_vals = df[col].dropna().astype(str).tolist()
            if any(any(re.search(term, val.lower()) for term in ["sales", "purchase", "capital", "rent", "bank"]) for val in sample_vals):
                ledger_col = col
                break

        # Accumulators
        totals: Dict[str, float] = {k: 0.0 for k in self.PATTERNS}
        unmapped = 0

        for _, row in df.iterrows():
            ledger_name = str(row[ledger_col]).strip()
            if not ledger_name or ledger_name.lower() in ["total", "grand total", "particulars", "ledger"]:
                continue

            # Extract highest numeric value in the row (Debit/Credit/Closing balance)
            row_numbers = []
            for col in df.columns:
                if col == ledger_col:
                    continue
                val = str(row[col]).replace(",", "").replace("₹", "").strip()
                try:
                    num = float(val)
                    if num > 0:
                        row_numbers.append(num)
                except ValueError:
                    continue

            if not row_numbers:
                continue

            amount = max(row_numbers)
            ledger_lower = ledger_name.lower()

            matched = False
            for category, regex_list in self.PATTERNS.items():
                if any(re.search(rx, ledger_lower) for rx in regex_list):
                    totals[category] += amount
                    matched = True
                    break

            if not matched:
                unmapped += 1

        # Fallbacks for zero amounts
        sales = max(totals["revenue"], 100000.0)
        cogs = totals["cogs"] if totals["cogs"] > 0 else (sales * 0.65)
        opex = totals["opex"] if totals["opex"] > 0 else (sales * 0.10)
        debtors = totals["debtors"] if totals["debtors"] > 0 else ((sales / 365.0) * 45.0)
        inventory = totals["inventory"] if totals["inventory"] > 0 else ((cogs / 365.0) * 60.0)
        creditors = totals["creditors"] if totals["creditors"] > 0 else ((cogs / 365.0) * 30.0)

        # Calculate ratios & working capital cycles
        cogs_pct = min(max(round(cogs / sales, 2), 0.30), 0.90)
        opex_pct = min(max(round(opex / sales, 2), 0.03), 0.30)
        
        debtor_days = int(min(max(round((debtors / sales) * 365), 15), 120))
        inventory_days = int(min(max(round((inventory / cogs) * 365), 15), 150))
        creditor_days = int(min(max(round((creditors / cogs) * 365), 15), 90))

        return ExtractedBaseFinancials(
            base_turnover=Decimal(str(round(sales, 2))),
            cogs=Decimal(str(round(cogs, 2))),
            opex=Decimal(str(round(opex, 2))),
            sundry_debtors=Decimal(str(round(debtors, 2))),
            closing_inventory=Decimal(str(round(inventory, 2))),
            sundry_creditors=Decimal(str(round(creditors, 2))),
            cogs_ratio=cogs_pct,
            opex_ratio=opex_pct,
            debtor_days=debtor_days,
            inventory_days=inventory_days,
            creditor_days=creditor_days,
            unmapped_ledgers_count=unmapped
        )