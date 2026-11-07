# backend/app/main.py
from fastapi import FastAPI
from backend.app.api.endpoints import router as compliance_router

app = FastAPI(
    title="KSP Consulting & Solutions — Autonomous Compliance Engine",
    description="Statutory GST Rule 36(4), Rule 88C, Escrow Gatekeeper & Dual-Regime ITR API",
    version="2.4.0"
)

app.include_router(compliance_router)

@app.get("/healthz")
def health_check():
    return {"status": "HEALTHY", "version": "2.4.0"}