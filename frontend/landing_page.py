import streamlit as st

def render_seo_headers_and_schemas():
    """
    Injects Google-compliant JSON-LD structured schemas for search engine crawlers.
    Targets keywords: 'ITR filing online Hyderabad', 'Rule 36(4) GST reconciliation software',
    'Bank statement to ITR JSON converter', 'Dual tax regime optimizer 2026'.
    """
    schema_markup = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "SoftwareApplication",
          "name": "KSP Compliance & Tax Suite",
          "operatingSystem": "Web Browser",
          "applicationCategory": "BusinessApplication",
          "offers": {
            "@type": "Offer",
            "price": "499",
            "priceCurrency": "INR"
          },
          "description": "Autonomous statutory compliance software for GST Rule 36(4) reconciliation, Rule 88C audits, 5-Year CMA loan modeling, and Dual-Regime ITR computation with instant CBDT JSON export."
        },
        {
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "Can I convert ICICI or Axis bank statements directly into an ITR-1 or ITR-4 filing JSON?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes. The KSP Autonomous Suite parses bank statement PDFs, detects payroll and interest credits, cross-checks them against AIS and Form 26AS, and outputs an official CBDT-compliant offline JSON upload payload."
              }
            },
            {
              "@type": "Question",
              "name": "How does the system decide between the Old Tax Regime and Section 115BAC New Regime?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "The engine runs both tax regimes in parallel, computes Section 10(13A) HRA, Section 24(b) home loan interest, and Chapter VI-A deductions, and automatically recommends the regime providing maximum post-tax savings."
              }
            }
          ]
        }
      ]
    }
    </script>
    """
    st.markdown(schema_markup, unsafe_allow_html=True)

def render_marketing_landing_page():
    render_seo_headers_and_schemas()

    # Hero Banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); padding: 45px 35px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #415a77;">
        <span style="background-color: #2a9d8f; color: white; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">100% Statutory Compliant</span>
        <h1 style="color: #ffffff; font-size: 34px; font-weight: 800; margin-top: 15px; margin-bottom: 10px; line-height: 1.2;">File Clean Tax Returns & Reconcile GST In Under 60 Seconds</h1>
        <p style="color: #e0e1dd; font-size: 16px; max-width: 850px; line-height: 1.6; margin-bottom: 25px;">
            Eliminate hours of manual data entry. Upload your Bank Statements, AIS, or Purchase Registers — our automated pre-audit engines handle the rest: from Rule 36(4) matching to CBDT-ready ITR JSON creation.
        </p>
        <div style="display: flex; gap: 15px; flex-wrap: wrap;">
            <a href="#pricing-section" style="background-color: #e63946; color: white; padding: 12px 26px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 15px;">Get Started (From ₹499)</a>
            <a href="#how-it-works" style="background-color: transparent; border: 1px solid #778da9; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 15px;">See How It Works</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Core Value Pillars
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        #### ⚡ Instant Statement Ingestion
        Parses Axis, ICICI, HDFC, SBI, and Kotak statements automatically. Accurately identifies payroll inflows and interest earnings without storing passwords or plain-text PII.
        """)
    with c2:
        st.markdown("""
        #### ⚖️ Dynamic Dual-Regime Optimizer
        Side-by-side computation of Old Regime vs Section 115BAC New Regime. Dynamically loads annual tax slab updates from centralized statutory rule engines.
        """)
    with c3:
        st.markdown("""
        #### 📑 1-Click CBDT JSON & Audit PDFs
        Download validated JSON files ready for direct portal upload, alongside clear, step-by-step computation packs designed for accounting teams.
        """)

    st.markdown("---")

    # Workflow Steps
    st.markdown("<h3 id='how-it-works'>How It Works</h3>", unsafe_allow_html=True)
    w1, w2, w3 = st.columns(3)
    with w1:
        st.info("**Step 1: Upload Files**\n\nDrop your password-protected bank statement and AIS/26AS PDF. All parsing runs directly in volatile memory.")
    with w2:
        st.info("**Step 2: Automated Pre-Audit**\n\nThe engine balances deductions, verifies Section 87A rebate limits, and flags high-value transaction discrepancies.")
    with w3:
        st.info("**Step 3: Upload & File**\n\nDownload the CBDT-compliant JSON schema and upload it directly to the e-Filing portal with zero manual data entry.")

    st.markdown("---")

    # Pricing Grid
    st.markdown("<h3 id='pricing-section'>Transparent Pricing for Professionals & Firms</h3>", unsafe_allow_html=True)
    p_col1, p_col2 = st.columns(2)

    with p_col1:
        st.markdown("""
        <div style="border: 2px solid #415a77; border-radius: 10px; padding: 25px; background-color: #1b263b;">
            <h4 style="color: #ffffff; margin-bottom: 5px;">Self-Service Individual ITR</h4>
            <p style="color: #a0aec0; font-size: 13px;">For Salaried Professionals, Freelancers & Consultants</p>
            <h2 style="color: #ffffff; font-size: 32px; margin: 15px 0;">₹499 <span style="font-size: 14px; color: #a0aec0; font-weight: 400;">/ filing pack</span></h2>
            <ul style="color: #e0e1dd; line-height: 1.8; font-size: 14px; margin-bottom: 20px;">
                <li>✓ Multi-bank statement auto-parsing</li>
                <li>✓ AIS & Form 26AS interest cross-reconciliation</li>
                <li>✓ Old vs New Regime tax savings comparison</li>
                <li>✓ Downloadable filing-ready CBDT JSON schema</li>
                <li>✓ Audit-grade Computation Pack with step-by-step guide</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.button("Pay & Launch ITR Engine (₹499)", key="btn_pay_itr", type="primary")

    with p_col2:
        st.markdown("""
        <div style="border: 2px solid #2a9d8f; border-radius: 10px; padding: 25px; background-color: #1b263b;">
            <span style="background-color: #2a9d8f; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;">MOST POPULAR FOR PRACTICES</span>
            <h4 style="color: #ffffff; margin-top: 8px; margin-bottom: 5px;">CA Firm & Tax Practice Unlimited</h4>
            <p style="color: #a0aec0; font-size: 13px;">For Tax Practitioners, Accountants & Compliance Bureaus</p>
            <h2 style="color: #ffffff; font-size: 32px; margin: 15px 0;">₹2,499 <span style="font-size: 14px; color: #a0aec0; font-weight: 400;">/ month</span></h2>
            <ul style="color: #e0e1dd; line-height: 1.8; font-size: 14px; margin-bottom: 20px;">
                <li>✓ Unlimited GST Rule 36(4) Inward ITC batch matching</li>
                <li>✓ Automated GSTR-1 vs 3B Rule 88C notice defense</li>
                <li>✓ 5-Year Bank CMA Working Capital model & Excel export</li>
                <li>✓ Statutory audit threshold evaluation & CA escrow gatekeeper</li>
                <li>✓ Priority processing & client audit report generation</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.button("Subscribe to CA Practice Suite (₹2,499/mo)", key="btn_pay_firm")