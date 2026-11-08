#!/usr/bin/env bash
streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1 &
uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}