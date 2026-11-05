import io
import pandas as pd
from decimal import Decimal
from datetime import date
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app.models.schemas import (
    StandardInvoice,
    ReconciliationSummary,
    EntityType,
    AuditWorkflowStatus
)
from backend.app.engines.gst_matcher import Rule36ReconciliationEngine
from backend.app.engines.statutory_guard import StatutoryAuditGatekeeper

app = FastAPI(
    title="KSP Consulting & Solutions - Engine Suite",
    version="1.0.0",
    description="Deterministic GST Rule 36(4) Matching & Statutory CA Audit Escrow Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gst_engine = Rule36ReconciliationEngine()
gatekeeper = StatutoryAuditGatekeeper()

class StatutoryCheckRequest(BaseModel):
    entity_name: str
    entity_type: EntityType
    annual_turnover: Decimal
    is_95_percent_digital: bool = True

class StatutoryCheckResponse(BaseModel):
    entity_name: str
    status: AuditWorkflowStatus
    reason: str

@app.get("/")
def health_check():
    return {"status": "online", "entity": "KSP Consulting & Solutions", "engine": "FastAPI + Deterministic Rules"}

@app.post("/api/v1/audit-check", response_model=StatutoryCheckResponse)
def check_statutory_audit(req: StatutoryCheckRequest):
    status, reason = gatekeeper.evaluate(
        entity_type=req.entity_type,
        annual_turnover=req.annual_turnover,
        is_95_percent_digital=req.is_95_percent_digital
    )
    return StatutoryCheckResponse(
        entity_name=req.entity_name,
        status=status,
        reason=reason
    )

@app.post("/api/v1/reconcile-json", response_model=ReconciliationSummary)
def reconcile_json(books: List[StandardInvoice], gstr2b: List[StandardInvoice]):
    return gst_engine.run(books, gstr2b)

def parse_excel_to_invoices(file_bytes: bytes) -> List[StandardInvoice]:
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception:
        df = pd.read_csv(io.BytesIO(file_bytes))

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    invoices = []
    for _, row in df.iterrows():
        taxable = Decimal(str(row.get("taxable_value", 0.0)))
        cgst = Decimal(str(row.get("cgst", 0.0)))
        sgst = Decimal(str(row.get("sgst", 0.0)))
        igst = Decimal(str(row.get("igst", 0.0)))
        tot_tax = Decimal(str(row.get("total_tax", cgst + sgst + igst)))
        tot_val = Decimal(str(row.get("total_value", taxable + tot_tax)))

        raw_date = row.get("invoice_date", date.today())
        if isinstance(raw_date, pd.Timestamp):
            inv_date = raw_date.date()
        elif isinstance(raw_date, str):
            inv_date = date.fromisoformat(raw_date[:10])
        else:
            inv_date = date.today()

        invoices.append(
            StandardInvoice(
                invoice_number=str(row.get("invoice_number", "")).strip(),
                supplier_gstin=str(row.get("supplier_gstin", "")).strip(),
                supplier_name=str(row.get("supplier_name", "")),
                invoice_date=inv_date,
                taxable_value=taxable,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                total_tax=tot_tax,
                total_value=tot_val
            )
        )
    return invoices

@app.post("/api/v1/reconcile-files", response_model=ReconciliationSummary)
async def reconcile_files(
    books_file: UploadFile = File(...),
    gstr2b_file: UploadFile = File(...)
):
    b_bytes = await books_file.read()
    g_bytes = await gstr2b_file.read()

    books_invs = parse_excel_to_invoices(b_bytes)
    gstr2b_invs = parse_excel_to_invoices(g_bytes)

    return gst_engine.run(books_invs, gstr2b_invs)
