#!/usr/bin/env bash

# 1. Boot Streamlit internally in the background
streamlit run frontend/app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false &

# 2. Boot FastAPI on Render's assigned $PORT
exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
