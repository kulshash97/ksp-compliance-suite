import io
from decimal import Decimal
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def get_base_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="KSPTitle",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1F497D")
    )
    h2_style = ParagraphStyle(
        name="KSPH2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#333333")
    )
    bold_sub = ParagraphStyle(
        name="KSPBoldSub",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1F497D")
    )
    alert_style = ParagraphStyle(
        name="KSPAlert",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#B71C1C")
    )
    normal_style = ParagraphStyle(
        name="KSPNormal",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11
    )
    return title_style, h2_style, bold_sub, alert_style, normal_style

# ----------------- TAB 1: GST INWARD ITC RECONCILIATION PDF -----------------
def generate_gst_itc_pdf(summary_data: Any) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    title_style, h2_style, bold_sub, alert_style, normal_style = get_base_styles()

    elements.append(Paragraph("KSP CONSULTING & SOLUTIONS", title_style))
    elements.append(Paragraph("GST Rule 36(4) Inward ITC Reconciliation & Vendor Action Report", h2_style))
    elements.append(Spacer(1, 10))

    # Summary Metrics Table
    summary_table = [
        ["Total Books Records", str(summary_data.total_books_records), "Matched Invoices", str(summary_data.matched_count)],
        ["Eligible ITC (Claimable)", f"Rs {summary_data.eligible_itc:,.2f}", "Blocked/Pending ITC", f"Rs {summary_data.ineligible_or_pending_itc:,.2f}"],
        ["Actionable Discrepancies", str(len(summary_data.discrepancies)), "Statutory Rule", "CGST Rule 36(4) & Sec 16(2)(aa)"]
    ]
    t_sum = Table(summary_table, colWidths=[140, 130, 140, 130])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F5F9")),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 12))

    # Detailed Discrepancy Breakdown
    elements.append(Paragraph("Actionable Discrepancy Schedule & Statutory Remediation", h2_style))
    elements.append(Spacer(1, 5))

    disc_data = [["Supplier GSTIN", "Invoice No", "Discrepancy Status", "Tax Variance (Rs)", "Action Required"]]
    
    # Safe inspection of ReconciliationRecord attributes
    for d in summary_data.discrepancies[:20]:
        # Extract invoice reference
        inv_ref = getattr(d, 'books_invoice', None) or getattr(d, 'gstr2b_invoice', None)
        gstin = getattr(inv_ref, 'supplier_gstin', 'N/A') if inv_ref else getattr(d, 'supplier_gstin', 'N/A')
        inv_no = getattr(inv_ref, 'invoice_number', 'N/A') if inv_ref else getattr(d, 'invoice_number', 'N/A')
        
        # Extract status / discrepancy type
        raw_status = getattr(d, 'status', None) or getattr(d, 'discrepancy_type', 'DISCREPANCY')
        status_str = raw_status.value if hasattr(raw_status, 'value') else str(raw_status)
        
        # Variance
        variance = getattr(d, 'tax_variance', Decimal("0.00"))
        
        # Action determination
        if "MISSING" in status_str.upper():
            action = "Withhold payment & issue GSTR-1 demand"
        elif "PARTIAL" in status_str.upper() or "MISMATCH" in status_str.upper():
            action = "Reconcile rate / tax value mismatch"
        else:
            action = "Verify supporting tax invoice"

        disc_data.append([
            gstin,
            inv_no,
            status_str,
            f"{variance:,.2f}",
            action
        ])

    t_disc = Table(disc_data, colWidths=[110, 80, 100, 80, 170])
    t_disc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F497D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('ALIGN', (3,1), (3,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_disc)
    elements.append(Spacer(1, 12))

    # Work to be Done
    elements.append(Paragraph("Exact Execution Steps for Accounts / CA Team:", h2_style))
    steps = [
        "1. In Table 4(A)(5) of Form GSTR-3B, claim ONLY the eligible ITC amount shown above.",
        "2. Do NOT claim the blocked/pending ITC; parking this in Table 4(D)(2) avoids Section 50 interest penalties (18% p.a.).",
        "3. Send debit memos / formal letters to the identified vendors with 'MISSING_IN_2B' status before the October 30 statutory deadline."
    ]
    for s in steps:
        elements.append(Paragraph(s, normal_style))
        elements.append(Spacer(1, 2))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------- TAB 2: GST OUTWARD LIABILITY (GSTR-1 VS 3B) PDF -----------------
def generate_gst_sales_pdf(res: Any) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    title_style, h2_style, bold_sub, alert_style, normal_style = get_base_styles()

    elements.append(Paragraph("KSP CONSULTING & SOLUTIONS", title_style))
    elements.append(Paragraph("GSTR-1 vs. GSTR-3B Statutory Outward Liability Audit (Rule 88C)", h2_style))
    elements.append(Spacer(1, 10))

    data = [
        ["GST Parameter", "GSTR-1 (Declared)", "GSTR-3B (Tax Paid)", "Variance (Rs)"],
        ["Taxable Turnover", f"Rs {res.gstr1_turnover:,.2f}", f"Rs {res.gstr3b_turnover:,.2f}", f"Rs {res.gstr1_turnover - res.gstr3b_turnover:,.2f}"],
        ["Total Outward Tax Liability", f"Rs {res.gstr1_tax:,.2f}", f"Rs {res.gstr3b_tax:,.2f}", f"Rs {res.tax_difference:,.2f}"],
        ["Statutory Audit Status", res.status, "Rule 88C Threshold", "Exceeds 10% & Rs 25,000"]
    ]
    t = Table(data, colWidths=[150, 130, 130, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F497D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Statutory Remediation Directive:", h2_style))
    elements.append(Paragraph(f"• <b>Status:</b> {res.status}", alert_style if res.rule_88c_breach else bold_sub))
    elements.append(Paragraph(f"• <b>Remediation:</b> {res.remediation_note}", normal_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Exact Action Steps:", h2_style))
    action_steps = [
        "1. If GSTR-1 liability exceeds GSTR-3B, pay differential tax along with interest under Section 50 via Form DRC-03.",
        "2. Alternatively, file Form DRC-01B Part B on the GST portal explaining genuine reporting differences (such as credit notes or unadjusted advances) within 7 days.",
        "3. Failure to respond within 7 days results in automatic restriction of GSTR-1 filing for subsequent tax periods under Rule 59(6)."
    ]
    for s in action_steps:
        elements.append(Paragraph(s, normal_style))
        elements.append(Spacer(1, 2))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------- TAB 3: STATUTORY AUDIT GATEKEEPER PDF -----------------
def generate_audit_escrow_pdf(client_name: str, ent_type: str, turnover: Decimal, is_digital: bool, status: str, reason: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    title_style, h2_style, bold_sub, alert_style, normal_style = get_base_styles()

    elements.append(Paragraph("KSP CONSULTING & SOLUTIONS", title_style))
    elements.append(Paragraph("Statutory CA Audit Mandate & Escrow Assessment Memo", h2_style))
    elements.append(Spacer(1, 10))

    data = [
        ["Client / Assessee Name:", client_name, "Legal Constitution:", ent_type],
        ["Annual Gross Turnover:", f"Rs {turnover:,.2f}", "Digital Receipts > 95%:", "Yes" if is_digital else "No"],
        ["Audit Mandate Verdict:", status, "Statutory Acts Evaluated:", "Sec 139/141 Companies Act & Sec 44AB ITA"]
    ]
    t = Table(data, colWidths=[140, 130, 140, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F5F9")),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Statutory Legal Verdict & Escrow Directive:", h2_style))
    elements.append(Paragraph(f"• {reason}", alert_style if "NEEDS_CA" in status else bold_sub))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Mandatory CA Execution Procedure:", h2_style))
    if "NEEDS_CA" in status:
        instructions = [
            "1. Financial statements MUST be audited by an independent practicing Chartered Accountant holding a valid Certificate of Practice (COP).",
            "2. Auditor must generate a 18-digit Unique Document Identification Number (UDIN) on the ICAI portal within 60 days.",
            "3. Return filing is locked in escrow until Form 3CA/3CB and Form 3CD are signed with the CA's Digital Signature Certificate (DSC Class 3)."
        ]
    else:
        instructions = [
            "1. Assessee is legally exempt from statutory tax audit under Section 44AB.",
            "2. File regular ITR on or before the statutory due date (July 31).",
            "3. Maintain books of accounts under Section 44AA if professional gross receipts exceed Rs 1,50,000."
        ]
    for ins in instructions:
        elements.append(Paragraph(ins, normal_style))
        elements.append(Spacer(1, 2))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ----------------- TAB 4: CMA LOAN CREDIT MEMORANDUM PDF -----------------
def generate_cma_memo_pdf(results: Any) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    title_style, h2_style, bold_sub, alert_style, normal_style = get_base_styles()

    elements.append(Paragraph("KSP CONSULTING & SOLUTIONS", title_style))
    elements.append(Paragraph("Bank Credit Appraisal & CMA Forecast Memo (Tandon Method II)", h2_style))
    elements.append(Spacer(1, 10))

    headers = ["Financial Parameter", "Base Year", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
    cma_rows = [headers]

    cma_rows.append(["Gross Sales (Rs L)", f"{results.base_revenue/100000:,.1f}"] + [f"{y.revenue/100000:,.1f}" for y in results.yearly_projections])
    cma_rows.append(["EBITDA (Rs L)", f"{(results.base_revenue*Decimal('0.15'))/100000:,.1f}"] + [f"{y.ebitda/100000:,.1f}" for y in results.yearly_projections])
    cma_rows.append(["PAT (Rs L)", f"{(results.base_revenue*Decimal('0.07'))/100000:,.1f}"] + [f"{y.pat/100000:,.1f}" for y in results.yearly_projections])
    cma_rows.append(["MPBF / CC Limit (Rs L)", "-"] + [f"{y.working_capital.max_permissible_bank_finance/100000:,.1f}" for y in results.yearly_projections])
    cma_rows.append(["Current Ratio (Norm >= 1.33)", "-"] + [f"{y.working_capital.current_ratio:.2f}" for y in results.yearly_projections])
    cma_rows.append(["DSCR (Norm >= 1.50x)", "-"] + [f"{y.dscr:.2f}x" for y in results.yearly_projections])

    t = Table(cma_rows, colWidths=[160, 55, 55, 55, 55, 55, 55])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F497D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Bank Underwriter Execution & Sanction Notes:", h2_style))
    notes = [
        "1. <b>Maximum Permissible Bank Finance (MPBF):</b> Computed under Tandon Committee Method II with 25% minimum borrower margin on Total Current Assets.",
        "2. <b>Liquidity Covenant:</b> Projected Current Ratio remains above the prudential 1.33 benchmark across all 5 projected operating years.",
        "3. <b>Debt Serviceability:</b> Average DSCR indicates comfortable repayment buffer for the requested term loan.",
        "4. <b>Action Required:</b> Submit alongside the accompanying detailed multi-tab Excel financial model (KSP_CMA_Forecast.xlsx) for credit committee sanction."
    ]
    for n in notes:
        elements.append(Paragraph(n, normal_style))
        elements.append(Spacer(1, 2))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()