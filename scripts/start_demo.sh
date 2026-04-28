#!/usr/bin/env bash
# Start the JobFlow demo backend (frontend-compatible)
# Usage: bash scripts/start_demo.sh
uvicorn jobflow.demo.backend:app --port 9000 --reload
