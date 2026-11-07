import io
from decimal import Decimal
from typing import List, Any, Dict
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# -------------------------------------------------------------
# 1. GST RULE 36(4) RECONCILIATION PDF
# -------------------------------------------------------------
def generate_gst_itc_pdf(summary) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1b263b'),
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("GST Rule 36(4) Inward ITC Reconciliation Report", title_style))
    story.append(Spacer(1, 10))

    summary_data = [
        ["Metric", "Value"],
        ["Total Invoices in Purchase Books", str(getattr(summary, 'total_books_records', 0))],
        ["Total Invoices in GSTR-2B", str(getattr(summary, 'total_gstr2b_records', 0))],
        ["Matched Invoices (Eligible ITC)", str(getattr(summary, 'matched_count', 0))],
        ["Actionable Discrepancies", str(getattr(summary, 'mismatched_count', 0))],
        ["Eligible ITC (Claimable)", f"Rs {getattr(summary, 'eligible_itc', Decimal('0.00')):,.2f}"],
        ["Blocked / Ineligible ITC", f"Rs {getattr(summary, 'ineligible_or_pending_itc', Decimal('0.00')):,.2f}"]
    ]

    t = Table(summary_data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b263b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(t)
    doc.build(story)

    val = buffer.getvalue()
    buffer.close()
    return val


# -------------------------------------------------------------
# 2. GST OUTWARD LIABILITY (RULE 88C) PDF
# -------------------------------------------------------------
def generate_gst_sales_pdf(s_res) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1b263b'),
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("GST Outward Liability Rule 88C Action Memo", title_style))
    story.append(Spacer(1, 10))

    data = [
        ["Field", "Value"],
        ["Audit Status", str(getattr(s_res, 'status', 'N/A'))],
        ["Rule 88C Notice Risk", "BREACH (DRC-01B)" if getattr(s_res, 'rule_88c_breach', False) else "COMPLIANT"],
        ["Turnover Variance", f"Rs {getattr(s_res, 'turnover_diff', Decimal('0.00')):,.2f}"],
        ["Tax Liability Variance", f"Rs {getattr(s_res, 'tax_diff', Decimal('0.00')):,.2f}"],
        ["Variance Percentage", f"{getattr(s_res, 'tax_diff_pct', Decimal('0.00')):.2f}%"]
    ]

    t = Table(data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b263b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(t)
    doc.build(story)

    val = buffer.getvalue()
    buffer.close()
    return val


# -------------------------------------------------------------
# 3. STATUTORY AUDIT & ESCROW PDF
# -------------------------------------------------------------
def generate_audit_escrow_pdf(ent_name: str, ent_type: str, turnover: Decimal, digital_tx: bool, status: str, reason: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1b263b'),
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph(f"Statutory Audit Mandate: {ent_name}", title_style))
    story.append(Spacer(1, 10))

    data = [
        ["Parameter", "Details"],
        ["Client Entity Name", ent_name],
        ["Legal Constitution", ent_type],
        ["Annual Gross Turnover", f"Rs {turnover:,.2f}"],
        [">=95% Digital Receipts/Payments", "Yes (Section 44AB Rs 10 Cr limit)" if digital_tx else "No (Section 44AB Rs 1 Cr limit)"],
        ["Statutory Workflow Status", status],
        ["Mandate / Action Note", reason]
    ]

    t = Table(data, colWidths=[180, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b263b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(t)
    doc.build(story)

    val = buffer.getvalue()
    buffer.close()
    return val


# -------------------------------------------------------------
# 4. CMA BANK LOAN CREDIT APPRAISAL MEMO PDF (FAIL-SAFE EXTRACTION)
# -------------------------------------------------------------
def _extract_cma_val(p: Any, *candidate_keys) -> Decimal:
    """Extracts a numeric field safely across Pydantic models, dicts, and objects."""
    d: Dict[str, Any] = {}
    if hasattr(p, 'model_dump'):
        d = p.model_dump()
    elif hasattr(p, 'dict'):
        d = p.dict()
    elif isinstance(p, dict):
        d = p
    else:
        d = getattr(p, '__dict__', {})

    for k in candidate_keys:
        if k in d and d[k] is not None:
            try:
                return Decimal(str(d[k]))
            except Exception:
                pass
        val = getattr(p, k, None)
        if val is not None:
            try:
                return Decimal(str(val))
            except Exception:
                pass

    return Decimal("0.00")


def generate_cma_memo_pdf(results: Any) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CMATitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1b263b'),
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("Bank Loan CMA Credit Appraisal Memo", title_style))
    story.append(Spacer(1, 12))

    # Safely convert to a list of period projections
    periods = results if isinstance(results, list) else getattr(results, 'periods', [])

    # Extract base revenue safely
    base_rev = Decimal("0.00")
    if hasattr(results, 'base_revenue'):
        base_rev = Decimal(str(results.base_revenue))
    elif periods:
        base_rev = _extract_cma_val(periods[0], 'gross_sales', 'turnover', 'revenue', 'sales')

    headers = ["Financial Metric", "Base Year"] + [f"Year {idx + 1}" for idx in range(len(periods))]
    cma_rows = [headers]

    # Gross Sales
    sales_row = ["Gross Sales (Rs L)", f"{float(base_rev)/100000:,.1f}"]
    for p in periods:
        sales_val = _extract_cma_val(p, 'gross_sales', 'turnover', 'revenue', 'sales')
        sales_row.append(f"{float(sales_val)/100000:,.1f}")
    cma_rows.append(sales_row)

    # Profit After Tax / Net Profit
    pat_row = ["Profit After Tax (Rs L)", "-"]
    for p in periods:
        pat_val = _extract_cma_val(p, 'pat', 'net_profit', 'profit_after_tax')
        pat_row.append(f"{float(pat_val)/100000:,.1f}")
    cma_rows.append(pat_row)

    # DSCR
    dscr_row = ["DSCR Ratio", "-"]
    for p in periods:
        dscr_val = _extract_cma_val(p, 'dscr', 'debt_service_coverage_ratio')
        dscr_row.append(f"{float(dscr_val):.2f}")
    cma_rows.append(dscr_row)

    table = Table(cma_rows, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b263b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    story.append(table)
    doc.build(story)

    val = buffer.getvalue()
    buffer.close()
    return val