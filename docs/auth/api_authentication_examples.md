# API Authentication Examples

This document provides practical examples of how to authenticate with the Trac API using AWS Cognito tokens.

## Authentication Methods

### 1. Session-Based Authentication (Current)

```bash
# Login and get session cookie
curl -c cookies.txt -X GET "http://localhost:8000/auth/login"
# This redirects to Cognito login page

# Use session cookie for API requests
curl -b cookies.txt -X GET "http://localhost:8000/api/tickets"
```

### 2. Bearer Token Authentication (To Be Implemented)

```bash
# Get tokens from Cognito (example using AWS CLI)
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 5adkv019v4rcu6o87ffg46ep02 \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPass123! \
  --region us-east-2

# Use access token for API requests
curl -H "Authorization: Bearer eyJraWQiOiI..." \
  -X GET "http://localhost:8000/api/tickets"
```

## Client Examples

### Python Client

```python
import requests
import json
from datetime import datetime, timedelta

class TracCognitoClient:
    def __init__(self, base_url, client_id, region):
        self.base_url = base_url
        self.client_id = client_id
        self.region = region
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
    
    def login(self, username, password):
        """Authenticate with Cognito and get tokens"""
        import boto3
        
        client = boto3.client('cognito-idp', region_name=self.region)
        
        try:
            response = client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            self.access_token = response['AuthenticationResult']['AccessToken']
            self.refresh_token = response['AuthenticationResult']['RefreshToken']
            self.token_expires = datetime.now() + timedelta(
                seconds=response['AuthenticationResult']['ExpiresIn']
            )
            
            return True
            
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def refresh_tokens(self):
        """Refresh access token using refresh token"""
        response = self.session.post(
            f"{self.base_url}/auth/refresh",
            json={'refresh_token': self.refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['access_token']
            self.token_expires = datetime.now() + timedelta(
                seconds=data['expires_in']
            )
            return True
        return False
    
    def _get_headers(self):
        """Get headers with valid token"""
        if datetime.now() >= self.token_expires:
            self.refresh_tokens()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_tickets(self):
        """Get all tickets"""
        response = self.session.get(
            f"{self.base_url}/api/tickets",
            headers=self._get_headers()
        )
        return response.json()
    
    def create_ticket(self, summary, description):
        """Create a new ticket"""
        data = {
            'summary': summary,
            'description': description,
            'type': 'defect',
            'priority': 'major'
        }
        
        response = self.session.post(
            f"{self.base_url}/api/tickets",
            headers=self._get_headers(),
            json=data
        )
        return response.json()

# Usage example
client = TracCognitoClient(
    base_url='http://localhost:8000',
    client_id='5adkv019v4rcu6o87ffg46ep02',
    region='us-east-2'
)

if client.login('testuser@example.com', 'TestPass123!'):
    tickets = client.get_tickets()
    print(f"Found {len(tickets)} tickets")
    
    new_ticket = client.create_ticket(
        summary='Test ticket from API',
        description='Created using Cognito authentication'
    )
    print(f"Created ticket #{new_ticket['id']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const jwt = require('jsonwebtoken');

class TracCognitoClient {
    constructor(baseUrl, clientId, region) {
        this.baseUrl = baseUrl;
        this.clientId = clientId;
        this.region = region;
        this.tokens = null;
    }
    
    async login(username, password) {
        // Using AWS SDK
        const AWS = require('aws-sdk');
        const cognito = new AWS.CognitoIdentityServiceProvider({
            region: this.region
        });
        
        try {
            const response = await cognito.initiateAuth({
                AuthFlow: 'USER_PASSWORD_AUTH',
                ClientId: this.clientId,
                AuthParameters: {
                    USERNAME: username,
                    PASSWORD: password
                }
            }).promise();
            
            this.tokens = {
                accessToken: response.AuthenticationResult.AccessToken,
                idToken: response.AuthenticationResult.IdToken,
                refreshToken: response.AuthenticationResult.RefreshToken,
                expiresAt: Date.now() + (response.AuthenticationResult.ExpiresIn * 1000)
            };
            
            return true;
        } catch (error) {
            console.error('Login failed:', error);
            return false;
        }
    }
    
    async refreshTokens() {
        try {
            const response = await axios.post(`${this.baseUrl}/auth/refresh`, {
                refresh_token: this.tokens.refreshToken
            });
            
            this.tokens.accessToken = response.data.access_token;
            this.tokens.expiresAt = Date.now() + (response.data.expires_in * 1000);
            
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            return false;
        }
    }
    
    async getAuthHeaders() {
        // Check if token needs refresh
        if (Date.now() >= this.tokens.expiresAt - 60000) {
            await this.refreshTokens();
        }
        
        return {
            'Authorization': `Bearer ${this.tokens.accessToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getTickets() {
        const headers = await this.getAuthHeaders();
        const response = await axios.get(`${this.baseUrl}/api/tickets`, { headers });
        return response.data;
    }
    
    async createTicket(summary, description) {
        const headers = await this.getAuthHeaders();
        const data = {
            summary,
            description,
            type: 'defect',
            priority: 'major'
        };
        
        const response = await axios.post(`${this.baseUrl}/api/tickets`, data, { headers });
        return response.data;
    }
    
    async updateTicket(ticketId, changes) {
        const headers = await this.getAuthHeaders();
        const response = await axios.put(
            `${this.baseUrl}/api/tickets/${ticketId}`, 
            changes, 
            { headers }
        );
        return response.data;
    }
}

// Usage
(async () => {
    const client = new TracCognitoClient(
        'http://localhost:8000',
        '5adkv019v4rcu6o87ffg46ep02',
        'us-east-2'
    );
    
    if (await client.login('testuser@example.com', 'TestPass123!')) {
        // Get all tickets
        const tickets = await client.getTickets();
        console.log(`Found ${tickets.length} tickets`);
        
        // Create a new ticket
        const newTicket = await client.createTicket(
            'API Test Ticket',
            'Created via Node.js client with Cognito auth'
        );
        console.log(`Created ticket #${newTicket.id}`);
        
        // Update the ticket
        const updated = await client.updateTicket(newTicket.id, {
            priority: 'critical',
            component: 'api'
        });
        console.log('Ticket updated:', updated);
    }
})();
```

### cURL Examples

```bash
# 1. Get ID token from Cognito (using AWS CLI)
TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id 5adkv019v4rcu6o87ffg46ep02 \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPass123! \
  --region us-east-2 \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# 2. List all tickets
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/tickets

# 3. Get specific ticket
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/tickets/123

# 4. Create a new ticket
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "New bug found",
    "description": "Details about the bug",
    "type": "defect",
    "priority": "major"
  }' \
  http://localhost:8000/api/tickets

# 5. Update a ticket
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "closed",
    "resolution": "fixed"
  }' \
  http://localhost:8000/api/tickets/123

# 6. Add a comment
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "This has been fixed in version 1.2.3"
  }' \
  http://localhost:8000/api/tickets/123/comments
```

## Postman Collection

```json
{
  "info": {
    "name": "Trac Cognito API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{access_token}}",
        "type": "string"
      }
    ]
  },
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Get Tokens",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "const response = pm.response.json();",
                  "pm.environment.set('access_token', response.AuthenticationResult.AccessToken);",
                  "pm.environment.set('id_token', response.AuthenticationResult.IdToken);",
                  "pm.environment.set('refresh_token', response.AuthenticationResult.RefreshToken);"
                ],
                "type": "text/javascript"
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/x-amz-json-1.1"
              },
              {
                "key": "X-Amz-Target",
                "value": "AWSCognitoIdentityProviderService.InitiateAuth"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"AuthFlow\": \"USER_PASSWORD_AUTH\",\n  \"ClientId\": \"5adkv019v4rcu6o87ffg46ep02\",\n  \"AuthParameters\": {\n    \"USERNAME\": \"{{username}}\",\n    \"PASSWORD\": \"{{password}}\"\n  }\n}"
            },
            "url": {
              "raw": "https://cognito-idp.us-east-2.amazonaws.com/",
              "protocol": "https",
              "host": ["cognito-idp", "us-east-2", "amazonaws", "com"],
              "path": [""]
            }
          }
        },
        {
          "name": "Refresh Token",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"refresh_token\": \"{{refresh_token}}\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/auth/refresh",
              "host": ["{{base_url}}"],
              "path": ["auth", "refresh"]
            }
          }
        }
      ]
    },
    {
      "name": "Tickets",
      "item": [
        {
          "name": "List Tickets",
          "request": {
            "method": "GET",
            "header": [],
            "url": {
              "raw": "{{base_url}}/api/tickets",
              "host": ["{{base_url}}"],
              "path": ["api", "tickets"]
            }
          }
        },
        {
          "name": "Create Ticket",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"summary\": \"Test ticket\",\n  \"description\": \"Created from Postman\",\n  \"type\": \"defect\",\n  \"priority\": \"major\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/api/tickets",
              "host": ["{{base_url}}"],
              "path": ["api", "tickets"]
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000"
    },
    {
      "key": "username",
      "value": "testuser@example.com"
    }
  ]
}
```

## Error Handling

### Common Error Responses

```json
// 401 Unauthorized - Invalid or expired token
{
  "error": "Token has expired",
  "code": "TOKEN_EXPIRED",
  "message": "Please refresh your token or login again"
}

// 403 Forbidden - Insufficient permissions
{
  "error": "Access denied",
  "code": "INSUFFICIENT_PERMISSIONS",
  "message": "You don't have permission to perform this action"
}

// 400 Bad Request - Invalid request
{
  "error": "Invalid request",
  "code": "INVALID_REQUEST",
  "message": "Missing required field: summary"
}
```

### Client-Side Error Handling

```javascript
async function handleApiRequest(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            switch (response.status) {
                case 401:
                    // Token expired, try to refresh
                    await refreshToken();
                    // Retry the request
                    return handleApiRequest(url, options);
                    
                case 403:
                    // Permission denied
                    throw new Error('You do not have permission to perform this action');
                    
                case 404:
                    // Resource not found
                    throw new Error('The requested resource was not found');
                    
                default:
                    // Other errors
                    const error = await response.json();
                    throw new Error(error.message || 'An error occurred');
            }
        }
        
        return response.json();
        
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}
```

## Testing Authentication

### Manual Testing Steps

1. **Test Login Flow**
   ```bash
   # Open browser and navigate to login
   open http://localhost:8000/auth/login
   # Should redirect to Cognito hosted UI
   # After login, should redirect back to Trac
   ```

2. **Test API with Token**
   ```bash
   # Get token and test API endpoint
   TOKEN="your-token-here"
   curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tickets
   # Should return 200 with ticket list
   ```

3. **Test Token Expiration**
   ```bash
   # Use an expired token
   EXPIRED_TOKEN="expired-token"
   curl -v -H "Authorization: Bearer $EXPIRED_TOKEN" http://localhost:8000/api/tickets
   # Should return 401 Unauthorized
   ```

4. **Test Permission Checks**
   ```bash
   # Use token from user without admin rights
   USER_TOKEN="user-token"
   curl -v -H "Authorization: Bearer $USER_TOKEN" -X DELETE http://localhost:8000/api/tickets/1
   # Should return 403 Forbidden
   ```

### Automated Testing

```python
import pytest
import requests
from unittest.mock import patch

class TestCognitoAuthentication:
    @pytest.fixture
    def auth_token(self):
        # Get a valid token for testing
        return "test.token.here"
    
    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication"""
        response = requests.get('http://localhost:8000/api/tickets')
        assert response.status_code == 401
    
    def test_valid_token_accepted(self, auth_token):
        """Test that valid tokens are accepted"""
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = requests.get('http://localhost:8000/api/tickets', headers=headers)
        assert response.status_code == 200
    
    def test_malformed_token_rejected(self):
        """Test that malformed tokens are rejected"""
        headers = {'Authorization': 'Bearer malformed.token'}
        response = requests.get('http://localhost:8000/api/tickets', headers=headers)
        assert response.status_code == 401
    
    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected"""
        expired_token = "expired.token.here"
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = requests.get('http://localhost:8000/api/tickets', headers=headers)
        assert response.status_code == 401
```