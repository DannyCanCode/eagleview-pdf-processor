#!/usr/bin/env bash
set -e  # Exit on error

# Use Railway's $PORT if available; otherwise fall back to 8000
PORT="${PORT:-8000}"

# Start Gunicorn with Uvicorn workers
exec gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:"$PORT" \
    --workers 2 