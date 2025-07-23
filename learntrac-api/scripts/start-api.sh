#!/bin/bash

# Exit on error
set -e

echo "Starting LearnTrac API initialization..."

# Start the API server
echo "Starting LearnTrac API server on port 8001..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001