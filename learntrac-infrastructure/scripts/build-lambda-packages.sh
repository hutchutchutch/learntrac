#!/bin/bash
# Script to build Lambda deployment packages

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="${INFRA_DIR}/lambda"

echo "Building Lambda deployment packages..."

# Create layers directory
mkdir -p "${LAMBDA_DIR}/layers"

# Build OpenAI SDK layer
echo "Building OpenAI SDK layer..."
cd "${LAMBDA_DIR}/layers"
mkdir -p openai-sdk/python
pip install openai boto3 -t openai-sdk/python/
cd openai-sdk
zip -r ../openai-sdk-layer.zip .
cd ..
rm -rf openai-sdk

# Build Lambda function packages
echo "Building llm_generate Lambda package..."
cd "${LAMBDA_DIR}"
zip llm-generate.zip llm_generate.py

echo "Building llm_evaluate Lambda package..."
zip llm-evaluate.zip llm_evaluate.py

# Build example Cognito pre-token generation Lambda if it doesn't exist
if [ ! -f "${LAMBDA_DIR}/cognito-pre-token-generation.py" ]; then
    echo "Creating example Cognito pre-token generation Lambda..."
    cat > "${LAMBDA_DIR}/cognito-pre-token-generation.py" << 'EOF'
import json

def handler(event, context):
    """
    Cognito pre-token generation trigger
    Adds custom claims to the JWT token
    """
    # Add custom claims
    event['response']['claimsOverrideDetails'] = {
        'claimsToAddOrOverride': {
            'custom:role': event['request']['userAttributes'].get('custom:role', 'student'),
            'custom:organization': event['request']['userAttributes'].get('custom:organization', 'default')
        }
    }
    
    return event
EOF
fi

if [ ! -f "${LAMBDA_DIR}/cognito-pre-token-generation.zip" ]; then
    echo "Building Cognito pre-token generation Lambda package..."
    cd "${LAMBDA_DIR}"
    zip cognito-pre-token-generation.zip cognito-pre-token-generation.py
fi

# Build API handler example if it doesn't exist
if [ ! -f "${LAMBDA_DIR}/api-handler-example.py" ]; then
    echo "Creating example API handler Lambda..."
    cat > "${LAMBDA_DIR}/api-handler-example.py" << 'EOF'
import json

def handler(event, context):
    """
    Example API Gateway Lambda handler
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Hello from LearnTrac API',
            'path': event.get('path', '/'),
            'method': event.get('httpMethod', 'GET')
        })
    }
EOF
fi

echo "Lambda packages built successfully!"
echo ""
echo "Packages created:"
ls -la "${LAMBDA_DIR}"/*.zip
ls -la "${LAMBDA_DIR}/layers"/*.zip