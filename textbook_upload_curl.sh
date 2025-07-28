#!/bin/bash

# Textbook Upload Curl Commands
# ==============================

# Method 1: Using the development endpoint (no authentication required)
echo "Method 1: Development endpoint (recommended for testing)"
echo "--------------------------------------------------------"
cat << 'EOF'
curl -X POST "http://localhost:8001/api/trac/textbooks/upload-dev" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/textbook.pdf"
EOF

echo -e "\n\nMethod 2: Using the main endpoint with authentication"
echo "--------------------------------------------------------"
cat << 'EOF'
curl -X POST "http://localhost:8001/api/trac/textbooks/upload" \
  -H "Cookie: trac_auth=test_token" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/textbook.pdf"
EOF

echo -e "\n\nMethod 3: With Bearer token authentication"
echo "--------------------------------------------------------"
cat << 'EOF'
curl -X POST "http://localhost:8001/api/trac/textbooks/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/textbook.pdf"
EOF

echo -e "\n\nMethod 4: With additional metadata (if supported)"
echo "--------------------------------------------------------"
cat << 'EOF'
curl -X POST "http://localhost:8001/api/trac/textbooks/upload" \
  -H "Cookie: trac_auth=test_token" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/textbook.pdf" \
  -F "title=Introduction to Computer Science" \
  -F "subject=Computer Science" \
  -F "authors=John Doe, Jane Smith"
EOF

echo -e "\n\nActual working example:"
echo "--------------------------------------------------------"
echo "# From your local machine to the running API:"
cat << 'EOF'
curl -X POST "http://localhost:8001/api/trac/textbooks/upload-dev" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./textbooks/Introduction_To_Computer_Science.pdf" \
  -v
EOF

echo -e "\n\nTo test the upload status:"
echo "--------------------------------------------------------"
cat << 'EOF'
# Check processing status (if the API returns a task ID)
curl -X GET "http://localhost:8001/api/trac/textbooks/status/{task_id}" \
  -H "Cookie: trac_auth=test_token" \
  -H "accept: application/json"
EOF

echo -e "\n\nNotes:"
echo "------"
echo "1. Replace '/path/to/your/textbook.pdf' with the actual path to your PDF file"
echo "2. The development endpoint (/upload-dev) doesn't require authentication"
echo "3. The main endpoint (/upload) requires either a Cookie or Bearer token"
echo "4. Add -v flag for verbose output to see request/response details"
echo "5. Add -o response.json to save the response to a file"
echo "6. Maximum file size is typically limited by the server configuration"