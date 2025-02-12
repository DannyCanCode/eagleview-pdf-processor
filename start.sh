#!/bin/bash

# Use PORT from environment or default to 8000
PORT="${PORT:-8000}"

# Start gunicorn with uvicorn workers
exec gunicorn main:app \
    --bind "0.0.0.0:$PORT" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 1 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - 