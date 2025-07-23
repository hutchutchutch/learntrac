#!/bin/bash
set -e

echo "Starting LearnTrac API..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --log-level info \
    --access-log \
    --use-colors