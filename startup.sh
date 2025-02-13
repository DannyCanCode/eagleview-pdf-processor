#!/bin/bash

# Start Gunicorn with Uvicorn workers
exec gunicorn main:app \
    --bind=0.0.0.0:$PORT \
    --workers=4 \
    --worker-class=uvicorn.workers.UvicornWorker \
    --timeout=600 \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info 