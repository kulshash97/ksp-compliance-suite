import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_cma_excel_workbook(results: list) -> bytes:
    wb = Workbook()
    
    # Define styles
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    subtotal_font = Font(name="Calibri", size=10, bold=True)
    subtotal_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    regular_font = Font(name="Calibri", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )

    years = [r.year_label for r in results]
    headers = ["Line Item"] + years

    # --- Sheet 1: Operating Statement ---
    ws1 = wb.active
    ws1.title = "Operating Statement (P&L)"
    ws1.append(headers)

    pnl_rows = [
        ("Gross Turnover / Sales", [float(r.gross_sales) for r in results], True),
        ("Cost of Goods Sold (COGS)", [float(r.cogs) for r in results], False),
        ("Gross Profit", [float(r.gross_profit) for r in results], True),
        ("Operating Expenses (SG&A)", [float(r.operating_expenses) for r in results], False),
        ("EBITDA", [float(r.ebitda) for r in results], True),
        ("Depreciation", [float(r.depreciation) for r in results], False),
        ("EBIT", [float(r.ebit) for r in results], True),
        ("Term Loan Interest", [float(r.interest_term_loan) for r in results], False),
        ("Working Capital (CC) Interest", [float(r.interest_working_capital) for r in results], False),
        ("Profit Before Tax (PBT)", [float(r.pbt) for r in results], True),
        ("Tax Provision (25%)", [float(r.tax_expense) for r in results], False),
        ("Profit After Tax (PAT)", [float(r.pat) for r in results], True),
        ("PAT Margin %", [f"{r.net_profit_margin_pct}%" for r in results], False)
    ]

    for label, vals, is_bold in pnl_rows:
        ws1.append([label] + vals)

    # --- Sheet 2: Working Capital & MPBF ---
    ws2 = wb.create_sheet(title="Working Capital Assessment")
    ws2.append(["Working Capital Parameter"] + years)

    wc_rows = [
        ("Total Current Assets (TCA)", [float(r.total_current_assets) for r in results], True),
        ("Current Liabilities (Non-Bank)", [float(r.total_current_liabilities_non_bank) for r in results], False),
        ("Working Capital Gap (WCG)", [float(r.working_capital_gap) for r in results], True),
        ("Borrower Margin (25% of TCA)", [float(r.margin_money_borrower) for r in results], False),
        ("Maximum Permissible Bank Finance (MPBF)", [float(r.max_permissible_bank_finance) for r in results], True),
        ("Bank Current Ratio", [float(r.current_ratio) for r in results], True),
        ("Debt Service Coverage Ratio (DSCR)", [f"{r.dscr}x" for r in results], True),
        ("Interest Coverage Ratio", [f"{r.interest_coverage_ratio}x" for r in results], False)
    ]

    for label, vals, is_bold in wc_rows:
        ws2.append([label] + vals)

    # Format both sheets
    for ws in [ws1, ws2]:
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")
            cell.border = thin_border

        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            first_cell = row[0]
            is_summary = any(kw in first_cell.value for kw in ["Gross Profit", "EBITDA", "EBIT", "PAT", "MPBF", "Current Ratio", "WCG", "Total Current"])
            
            for col_idx, cell in enumerate(row):
                cell.border = thin_border
                if is_summary:
                    cell.font = subtotal_font
                    cell.fill = subtotal_fill
                else:
                    cell.font = regular_font
                    
                if col_idx > 0 and isinstance(cell.value, (int, float)):
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal="right")

        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()