import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from decimal import Decimal
from datetime import date

from backend.app.models.schemas import StandardInvoice, EntityType, AuditWorkflowStatus
from backend.app.engines.gst_matcher import Rule36ReconciliationEngine
from backend.app.engines.statutory_guard import StatutoryAuditGatekeeper
from backend.app.engines.cma_engine import CMAEngine
from backend.app.engines.cma_exporter import build_cma_excel_workbook
from backend.app.engines.trial_balance_parser import TrialBalanceParser
from backend.app.engines.itr_engine import ITREngine
from backend.app.engines.itr_pdf_generator import generate_itr_computation_pdf
from backend.app.engines.itr_json_exporter import generate_efiling_json
from backend.app.engines.form26as_matcher import Form26ASParser
from backend.app.engines.exemption_optimizer import ExemptionOptimizer
from backend.app.engines.gst_sales_matcher import GSTSalesReconciliationEngine
from backend.app.engines.suite_pdf_generator import (
    generate_gst_itc_pdf,
    generate_gst_sales_pdf,
    generate_audit_escrow_pdf,
    generate_cma_memo_pdf
)
from backend.app.core.payment_gateway import RazorpayPaymentManager
from frontend.landing_page import render_marketing_landing_page

st.set_page_config(page_title="KSP Consulting & Solutions | Compliance Hub", layout="wide", page_icon="⚖️")

# Top Navigation: Switch between Marketing Overview and Compliance Suite
view_mode = st.sidebar.radio("Navigation", ["🏢 KSP Overview & Pricing", "⚙️ Compliance & Filing Hub"], index=1)

if view_mode == "🏢 KSP Overview & Pricing":
    render_marketing_landing_page()
    st.stop()

# ----------------- LICENSE & ACCESS TOKEN GATE -----------------
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 License & Access Token")
user_token = st.sidebar.text_input("Enter Active License Token", type="password")

clean_token = user_token.strip() if user_token else None
token_data = RazorpayPaymentManager.validate_access_token(clean_token) if clean_token else None

if token_data:
    st.sidebar.success(f"✅ Active License: {token_data.get('tier')} ({token_data.get('scope')})")
else:
    st.sidebar.info("Free Preview Mode (Downloads locked to authorized tokens)")

st.title("⚖️ KSP Consulting & Solutions — Autonomous Suite")
st.caption("Rule 36(4) Inward ITC • GSTR-1 vs 3B Liability • Statutory Escrow • 5-Year CMA • Autonomous ITR Hub")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 GST Rule 36(4) Inward ITC",
    "📑 GST Outward Liability (GSTR-1 vs 3B)",
    "🏛️ Statutory Audit Threshold Check", 
    "📈 Loan CMA & 5-Year Forecast Engine",
    "💼 Autonomous ITR Dual-Regime & Filing Hub"
])

# ----------------- TAB 1: GST INWARD ITC -----------------
with tab1:
    st.subheader("Purchase Books vs. GSTR-2B Matching")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Upload Purchase Register (Excel / CSV)**")
        b_file = st.file_uploader("Upload Purchase Books", type=["xlsx", "csv"], key="books")
    with col2:
        st.markdown("**2. Upload GSTR-2B Statement (Excel / CSV)**")
        g_file = st.file_uploader("Upload GSTR-2B", type=["xlsx", "csv"], key="gstr2b")

    if st.button("🚀 Run Live Reconciliation", type="primary"):
        if not b_file or not g_file:
            st.error("Please upload both Purchase Books and GSTR-2B files.")
        else:
            with st.spinner("Processing matching..."):
                try:
                    df_b = pd.read_excel(b_file) if b_file.name.endswith(".xlsx") else pd.read_csv(b_file)
                    df_g = pd.read_excel(g_file) if g_file.name.endswith(".xlsx") else pd.read_csv(g_file)
                    df_b.columns = [c.strip().lower().replace(" ", "_") for c in df_b.columns]
                    df_g.columns = [c.strip().lower().replace(" ", "_") for c in df_g.columns]

                    def to_invoices(df):
                        invs = []
                        for _, row in df.iterrows():
                            t = Decimal(str(row.get("taxable_value", 0.0)))
                            c = Decimal(str(row.get("cgst", 0.0)))
                            s = Decimal(str(row.get("sgst", 0.0)))
                            i = Decimal(str(row.get("igst", 0.0)))
                            tot_tax = Decimal(str(row.get("total_tax", c + s + i)))
                            tot_val = Decimal(str(row.get("total_value", t + tot_tax)))
                            invs.append(StandardInvoice(
                                invoice_number=str(row.get("invoice_number", "")).strip(),
                                supplier_gstin=str(row.get("supplier_gstin", "")).strip(),
                                supplier_name=str(row.get("supplier_name", "")),
                                invoice_date=date.today(),
                                taxable_value=t, cgst=c, sgst=s, igst=i,
                                total_tax=tot_tax, total_value=tot_val
                            ))
                        return invs

                    summary = Rule36ReconciliationEngine().run(to_invoices(df_b), to_invoices(df_g))
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Eligible ITC", f"₹ {summary.eligible_itc:,.2f}")
                    m2.metric("Blocked/Pending ITC", f"₹ {summary.ineligible_or_pending_itc:,.2f}")
                    m3.metric("Matched Invoices", f"{summary.matched_count} / {summary.total_books_records}")
                    m4.metric("Actionable Discrepancies", f"{len(summary.discrepancies)}")

                    st.markdown("---")
                    pdf_bytes_t1 = generate_gst_itc_pdf(summary)
                    st.download_button(
                        label="📄 Download Rule 36(4) Reconciliation & Vendor Action Report (PDF)",
                        data=pdf_bytes_t1,
                        file_name="KSP_GST_Rule36_Reconciliation_Report.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"Error during parsing: {str(e)}")

# ----------------- TAB 2: GST OUTWARD LIABILITY (RULE 88C) -----------------
with tab2:
    st.subheader("GSTR-1 vs. GSTR-3B Sales & Liability Reconciliation (Rule 88C)")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        g1_to = st.number_input("GSTR-1 Total Outward Taxable Value (₹)", min_value=0.0, value=15000000.0, step=100000.0)
        g1_tax = st.number_input("GSTR-1 Total Outward Tax Liability (₹)", min_value=0.0, value=2700000.0, step=50000.0)
    with c_s2:
        g3_to = st.number_input("GSTR-3B Taxable Turnover Reported (₹)", min_value=0.0, value=15000000.0, step=100000.0)
        g3_tax = st.number_input("GSTR-3B Tax Paid via Cash/ITC (₹)", min_value=0.0, value=2650000.0, step=50000.0)
        
    if st.button("⚖️ Run Outward Liability Audit"):
        s_res = GSTSalesReconciliationEngine.reconcile(
            Decimal(str(g1_to)), Decimal(str(g1_tax)), Decimal(str(g3_to)), Decimal(str(g3_tax))
        )
        if s_res.rule_88c_breach:
            st.error(f"🚨 **STATUS: {s_res.status}**")
            st.warning(s_res.remediation_note)
        else:
            st.success(f"✅ **STATUS: {s_res.status}**")
            st.info(s_res.remediation_note)

        st.markdown("---")
        pdf_bytes_t2 = generate_gst_sales_pdf(s_res)
        st.download_button(
            label="📄 Download GSTR-1 vs GSTR-3B Rule 88C Action Memo (PDF)",
            data=pdf_bytes_t2,
            file_name="KSP_GST_Rule88C_Liability_Memo.pdf",
            mime="application/pdf",
            type="primary"
        )

# ----------------- TAB 3: AUDIT GATEKEEPER -----------------
with tab3:
    st.subheader("Statutory Compliance & Audit Escrow Evaluator")
    with st.form("audit_form"):
        ent_name = st.text_input("Client / Entity Name", value="ABC Traders")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            ent_type = st.selectbox("Entity Legal Structure", options=[EntityType.PROPRIETORSHIP, EntityType.PARTNERSHIP, EntityType.LLP, EntityType.PVT_LTD, EntityType.PUBLIC_LTD])
        with col_e2:
            turnover = st.number_input("Annual Turnover (₹)", min_value=0.0, value=15000000.0, step=100000.0)
        digital_tx = st.checkbox("More than 95% of aggregate receipts/payments are digital (Sec 44AB 10 Cr threshold)", value=True)
        submitted = st.form_submit_button("Evaluate Audit Mandate")

    if submitted:
        audit_res = StatutoryAuditGatekeeper().evaluate(entity_type=ent_type, annual_turnover=Decimal(str(turnover)), is_95_percent_digital=digital_tx)
        status = audit_res[0]
        reason = audit_res[1]
        
        status_val = status.value if hasattr(status, 'value') else str(status)
        if status == AuditWorkflowStatus.NEEDS_CA_AUDIT:
            st.warning(f"🔒 **STATUS: {status_val}**")
            st.info(f"**Escrow Action:** {reason}")
        else:
            st.success(f"🔓 **STATUS: {status_val}**")
            st.write(reason)

        st.markdown("---")
        pdf_bytes_t3 = generate_audit_escrow_pdf(ent_name, ent_type.value, Decimal(str(turnover)), digital_tx, status_val, reason)
        st.download_button(
            label="📄 Download Statutory CA Audit Mandate & Escrow Memo (PDF)",
            data=pdf_bytes_t3,
            file_name=f"KSP_Audit_Mandate_{ent_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary"
        )

# ----------------- TAB 4: CMA FORECAST ENGINE -----------------
with tab4:
    st.subheader("📈 Bank Loan CMA Data & 5-Year Working Capital Forecasting")
    with st.expander("⚡ Auto-Populate from Tally / Zoho Books Trial Balance (Optional)", expanded=False):
        tb_file = st.file_uploader("Upload Trial Balance (Excel or CSV)", type=["xlsx", "csv"], key="tb_upload")
        if tb_file and st.button("Extract Financials & Auto-Fill Parameters"):
            try:
                extracted = TrialBalanceParser().parse(tb_file.read(), tb_file.name)
                st.session_state["base_rev"] = float(extracted.base_turnover)
                st.session_state["cogs_pct"] = int(extracted.cogs_ratio * 100)
                st.session_state["opex_pct"] = int(extracted.opex_ratio * 100)
                st.session_state["d_days"] = extracted.debtor_days
                st.session_state["inv_days"] = extracted.inventory_days
                st.session_state["cr_days"] = extracted.creditor_days
                st.success(f"✅ Extracted Base Sales: ₹ {extracted.base_turnover:,.2f}")
            except Exception as ex:
                st.error(f"Error parsing trial balance: {str(ex)}")

    with st.expander("⚙️ Model Parameters & Loan Assumptions", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            base_rev = st.number_input("Base Year Sales (₹)", min_value=100000.0, value=st.session_state.get("base_rev", 15000000.0), step=500000.0)
            cogs_ratio = st.slider("COGS (% of Turnover)", 30, 85, st.session_state.get("cogs_pct", 68)) / 100.0
            opex_ratio = st.slider("OpEx (% of Turnover)", 3, 25, st.session_state.get("opex_pct", 9)) / 100.0
        with c2:
            term_loan = st.number_input("Requested Term Loan (₹)", min_value=0.0, value=2500000.0, step=250000.0)
            loan_roi = st.slider("Term Loan ROI (% p.a.)", 7.0, 18.0, 10.5, 0.25) / 100.0
            loan_tenure = st.selectbox("Tenure (Years)", [3, 5, 7], index=1)
        with c3:
            d_days = st.slider("Debtor Days", 15, 120, st.session_state.get("d_days", 45))
            inv_days = st.slider("Inventory Days", 15, 150, st.session_state.get("inv_days", 60))
            cr_days = st.slider("Creditor Days", 15, 90, st.session_state.get("cr_days", 30))
            
    if st.button("📊 Generate 5-Year CMA Report", type="primary"):
        growth = [Decimal("0.15"), Decimal("0.15"), Decimal("0.12"), Decimal("0.12"), Decimal("0.10")]
        results = CMAEngine().project_5_years(
            base_revenue=Decimal(str(base_rev)), annual_growth_rates=growth, cogs_pct=Decimal(str(cogs_ratio)),
            opex_pct=Decimal(str(opex_ratio)), debtor_days=d_days, inventory_days=inv_days, creditor_days=cr_days,
            term_loan_principal=Decimal(str(term_loan)), term_loan_interest_rate=Decimal(str(loan_roi)), tenure_years=loan_tenure
        )
        st.markdown("---")
        cma_col1, cma_col2 = st.columns(2)
        with cma_col1:
            excel_bytes = build_cma_excel_workbook(results)
            st.download_button("📥 Download Formatted CMA Financial Model (.xlsx)", excel_bytes, "KSP_CMA_Forecast.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        with cma_col2:
            pdf_bytes_t4 = generate_cma_memo_pdf(results)
            st.download_button("📄 Download Bank Credit Appraisal Memo (PDF)", pdf_bytes_t4, "KSP_Bank_CMA_Appraisal_Memo.pdf", "application/pdf")

# ----------------- TAB 5: ITR DUAL-REGIME FILING HUB -----------------
with tab5:
    st.subheader("💼 Autonomous ITR Dual-Regime Optimizer & Filing Engine")
    st.caption("Multi-Bank Parsing • Form 26AS/AIS Cross-Check • HRA/24(b) Optimization • E-Filing JSON Generation")

    with st.expander("👤 Client Demographic & File Ingestion", expanded=True):
        ci1, ci2, ci3 = st.columns(3)
        with ci1:
            c_name = st.text_input("Taxpayer Legal Name (Auto-fills if empty)", value="")
        with ci2:
            c_pan = st.text_input("Taxpayer PAN (Auto-fills if empty)", value="")
        with ci3:
            c_password = st.text_input("PDF Password (e.g. pan+dob)", type="password")

        f1, f2, f3, f4 = st.columns(4)
        with f1:
            bank_pdf = st.file_uploader("1. Bank Statement (PDF)", type=["pdf"], key="itr_bank")
        with f2:
            ais_pdf = st.file_uploader("2. AIS / TIS (PDF)", type=["pdf"], key="itr_ais")
        with f3:
            f26as_pdf = st.file_uploader("3. Form 26AS (PDF)", type=["pdf"], key="itr_26as")
        with f4:
            pnl_file = st.file_uploader("4. Stock Capital Gains (XLSX)", type=["xlsx", "csv"], key="itr_cg")

    with st.expander("🏠 Old Regime Tax Exemptions & Deductions Optimizer (Optional Override)", expanded=True):
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            actual_rent = st.number_input("Annual Rent Paid (₹)", min_value=0.0, value=0.0, step=20000.0)
            hra_rec = st.number_input("Actual HRA Received from Employer (₹)", min_value=0.0, value=0.0, step=20000.0)
        with e2:
            basic_sal = st.number_input("Basic Salary component (₹)", min_value=0.0, value=0.0, step=50000.0)
            is_metro = st.checkbox("Resides in Metro City (Delhi, Mumbai, Kolkata, Chennai)", value=False)
        with e3:
            home_loan_int = st.number_input("Home Loan Interest Paid - Sec 24(b) (₹)", min_value=0.0, value=0.0, step=25000.0)