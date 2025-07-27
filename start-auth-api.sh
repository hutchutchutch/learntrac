#!/bin/bash

# Start the LearnTrac API with auth routes

echo "Starting LearnTrac API with authentication support..."
echo "API will be available at: http://localhost:8001"
echo ""
echo "Auth endpoints:"
echo "  - GET  /auth/config    - View Cognito configuration"
echo "  - GET  /auth/login     - Start login flow"
echo "  - GET  /auth/callback  - OAuth callback (automatic)"
echo "  - GET  /auth/verify    - Check auth status"
echo "  - GET  /auth/user      - Get current user"
echo "  - GET  /auth/logout    - Logout"
echo ""
echo "Test page: file://$(pwd)/test-auth-flow-debug.html"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd learntrac-api/src
python minimal_api.py