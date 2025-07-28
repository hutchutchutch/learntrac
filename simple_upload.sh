#!/bin/bash

echo "Simple PDF Upload Test"
echo "====================="

# First restart the API to ensure latest code is loaded
echo "1. Restarting API container..."
docker restart learntrac-api

# Wait for API to be ready
echo "2. Waiting for API to be ready..."
sleep 15

# Check API health
echo "3. Checking API health..."
curl -s http://localhost:8001/health | python -m json.tool

# Upload the PDF
echo -e "\n4. Uploading PDF to development endpoint..."
curl -X POST "http://localhost:8001/api/trac/textbooks/upload-dev" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/textbooks/Introduction_To_Computer_Science.pdf" \
  -s | python -m json.tool

echo -e "\nUpload complete!"