#!/usr/bin/env bash

# Exit on error
set -e

# Debugging: Print environment variables
echo "Current environment:"
printenv | grep -E '^(PORT|PYTHON|PATH)='

# Get PORT from environment or default to 8000
if [ -z "${PORT}" ]; then
    echo "Warning: PORT not set, defaulting to 8000"
    PORT=8000
else
    echo "Using PORT=${PORT}"
fi

# Validate PORT is a number
if ! [[ "${PORT}" =~ ^[0-9]+$ ]]; then
    echo "Error: PORT must be a number, got '${PORT}'"
    exit 1
fi

# Start Gunicorn with Uvicorn workers
echo "Starting server on port ${PORT}"
exec gunicorn main:app \
    --bind "0.0.0.0:${PORT}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info 