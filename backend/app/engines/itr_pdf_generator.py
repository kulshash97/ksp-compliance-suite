import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from backend.app.engines.itr_engine import ITRReconciliationResult

def generate_itr_computation_pdf(client_name: str, pan: str, res: ITRReconciliationResult) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="TitleStyle", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#1F497D"))
    h2_style = ParagraphStyle(name="H2Style", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.HexColor("#333333"))
    alert_style = ParagraphStyle(name="AlertStyle", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.HexColor("#B71C1C"))
    normal_style = ParagraphStyle(name="NormalStyle", fontName="Helvetica", fontSize=8.5, leading=11)
    step_title_style = ParagraphStyle(name="StepTitle", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor("#1F497D"))
    step_box_style = ParagraphStyle(name="StepBox", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#222222"))

    # Header
    elements.append(Paragraph("KSP CONSULTING & SOLUTIONS", title_style))
    elements.append(Paragraph(f"Statutory Income Tax Pre-Audit & Filing Package ({res.assessment_year})", h2_style))
    elements.append(Spacer(1, 10))

    # Client Demographics Table
    info_data = [
        ["Taxpayer Name:", res.client_name, "PAN:", res.pan],
        ["Assessment Year:", f"{res.assessment_year} (FY {res.financial_year})", "Recommended Form:", res.recommended_form],
        ["Optimal Tax Regime:", res.recommended_regime, "Tax Advantage:", f"Rs {res.tax_savings:,.2f}"]
    ]
    t_info = Table(info_data, colWidths=[120, 160, 120, 140])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F5F9")),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # 1. Statement of Income
    elements.append(Paragraph("1. Reconciled Statement of Total Income", h2_style))
    elements.append(Spacer(1, 4))
    inc_data = [
        ["Heads of Income", "Amount (Rs)", "Verification Source"],
        ["Salary / Pension Income", f"{res.salary_income:,.2f}", "Payroll Inflow Audit / Form 16"],
        ["Professional Receipts (Section 194J)", f"{res.professional_receipts_194j:,.2f}", "AIS Active TDS Record"],
        ["Presumptive Professional Income (Sec 44ADA @ 50%)", f"{res.business_presumptive_income:,.2f}", "Calculated under 44ADA"],
        ["Sale of Immovable Property (Consideration)", f"{res.property_sale_consideration:,.2f}", "AIS SFT-012 (Sub-Registrar)"],
        ["Bank Savings Interest (Reconciled)", f"{res.savings_interest_bank:,.2f}", "Bank Statement Credit Audit"],
        ["Gross Total Income (GTI)", f"{res.gross_total_income:,.2f}", "Statutory GTI Aggregate"]
    ]
    t_inc = Table(inc_data, colWidths=[260, 120, 160])
    t_inc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F497D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EBF1F5")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    elements.append(t_inc)
    elements.append(Spacer(1, 10))

    # 2. Dual-Regime Audit
    elements.append(Paragraph("2. Dual-Regime Comparative Audit (Old vs. Sec 115BAC)", h2_style))
    elements.append(Spacer(1, 4))
    comp_data = [
        ["Tax Computation Parameter", "Old Tax Regime", "New Tax Regime (Sec 115BAC)"],
        ["Gross Total Income", f"Rs {res.gross_total_income:,.2f}", f"Rs {res.gross_total_income:,.2f}"],
        ["Total Deductions (Std Ded, 80C, 80D, HRA, 24b)", f"Rs {res.old_regime_deductions:,.2f}", "Rs 75,000 / 50,000 (Std Ded Only)"],
        ["Net Taxable Income", f"Rs {res.old_regime_taxable_income:,.2f}", f"Rs {res.new_regime_taxable_income:,.2f}"],
        ["Computed Tax Liability (inc. 4% Cess)", f"Rs {res.old_regime_tax:,.2f}", f"Rs {res.new_regime_tax:,.2f}"],
        ["Pre-paid Taxes (TDS / Advance Tax)", f"Rs {res.tds_as_per_ais:,.2f}", f"Rs {res.tds_as_per_ais:,.2f}"],
        ["Net Payable / (Refundable)", f"Rs {res.old_regime_tax - res.tds_as_per_ais:,.2f}", f"Rs {res.new_regime_tax - res.tds_as_per_ais:,.2f}"]
    ]
    t_comp = Table(comp_data, colWidths=[240, 150, 150])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
    ]))
    elements.append(t_comp)
    elements.append(Spacer(1, 10))

    # 3. Discrepancies & Audit Flags
    elements.append(Paragraph("3. Statutory Audit & Compliance Alerts", h2_style))
    elements.append(Spacer(1, 4))
    if res.audit_flags:
        for flg in res.audit_flags:
            elements.append(Paragraph(f"• {flg}", alert_style if "Capital" in flg or "Discrepancy" in flg else normal_style))
            elements.append(Spacer(1, 1))
    else:
        elements.append(Paragraph("• Clean audit. Bank statement interest matches AIS records with 0 variance.", normal_style))
    elements.append(Spacer(1, 10))

    # 4. Step-by-Step Portal Filing Blueprint (Direct Action Guide)
    elements.append(Paragraph("4. Step-by-Step E-Filing Portal Execution Blueprint", h2_style))
    elements.append(Spacer(1, 4))
    
    blueprint_table_data = [["Step #", "Portal Section / Schedule", "Exact Work & Numbers to Input"]]
    for idx, step in enumerate(res.step_by_step_filing_guide, start=1):
        blueprint_table_data.append([
            f"Step {idx}",
            step["step"],
            Paragraph(step["action"], normal_style)
        ])
        
    t_blueprint = Table(blueprint_table_data, colWidths=[50, 140, 350])
    t_blueprint.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F497D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BFBFBF")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_blueprint)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()