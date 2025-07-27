#!/bin/bash
set -e

echo "================================================"
echo "LearnTrac AWS Docker Launch Script"
echo "================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Step 1: Get AWS credentials
echo "Step 1: Fetching AWS credentials..."
echo ""

# Get RDS password from Secrets Manager
DB_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id hutch-learntrac-dev-db-credentials \
    --region us-east-2 \
    --query SecretString --output text 2>/dev/null)

if [ -z "$DB_SECRET" ]; then
    print_error "Failed to retrieve database credentials from AWS Secrets Manager"
    print_warning "Make sure you have access to the secret: hutch-learntrac-dev-db-credentials"
    exit 1
fi

# Parse the secret
DB_PASSWORD=$(echo $DB_SECRET | jq -r .password)
DB_USERNAME=$(echo $DB_SECRET | jq -r .username)
DB_HOST=$(echo $DB_SECRET | jq -r .host)
DB_NAME=$(echo $DB_SECRET | jq -r .dbname)

print_status "Retrieved database credentials"

# Get Neo4j credentials from Secrets Manager
NEO4J_SECRET=$(aws secretsmanager get-secret-value \
    --secret-id hutch-learntrac-dev-neo4j-credentials \
    --region us-east-2 \
    --query SecretString --output text 2>/dev/null)

if [ -z "$NEO4J_SECRET" ]; then
    print_warning "Could not retrieve Neo4j credentials - will use mock data"
    NEO4J_URI=""
    NEO4J_USER=""
    NEO4J_PASSWORD=""
else
    # Parse Neo4j credentials
    NEO4J_URI=$(echo $NEO4J_SECRET | jq -r .uri)
    NEO4J_USER=$(echo $NEO4J_SECRET | jq -r .username)
    NEO4J_PASSWORD=$(echo $NEO4J_SECRET | jq -r .password)
    print_status "Retrieved Neo4j credentials"
fi

# Step 2: Create .env.aws file
echo ""
echo "Step 2: Creating environment configuration..."

cat > .env.aws << EOF
# AWS RDS PostgreSQL Configuration
DB_HOST=${DB_HOST}
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USERNAME}
DB_PASSWORD=${DB_PASSWORD}

# AWS Cognito Configuration
COGNITO_REGION=us-east-2
COGNITO_USER_POOL_ID=us-east-2_IvxzMrWwg
COGNITO_CLIENT_ID=5adkv019v4rcu6o87ffg46ep02
COGNITO_DOMAIN=hutch-learntrac-dev-auth

# AWS ElastiCache Redis Configuration
REDIS_URL=redis://hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com:6379
ELASTICACHE_ENDPOINT=hutch-learntrac-dev-redis.wda3jc.0001.use2.cache.amazonaws.com

# Neo4j Configuration
NEO4J_URI=${NEO4J_URI}
NEO4J_USER=${NEO4J_USER}
NEO4J_PASSWORD=${NEO4J_PASSWORD}

# LearnTrac API Configuration
API_ENDPOINT=http://learning-api:8001/api/trac
LEARNING_SERVICE_URL=http://learning-api:8001
LEARNING_API_URL=http://learning-api:8001/api/learntrac

# Environment Settings
ENVIRONMENT=development
AWS_REGION=us-east-2
LOG_LEVEL=INFO

# Trac Configuration
TRAC_ADMIN_USER=admin
TRAC_ADMIN_PASSWORD=admin
EOF

print_status "Created .env.aws configuration file"

# Step 3: Build the plugin if needed
echo ""
echo "Step 3: Building PDF upload plugin..."

cd plugins/pdfuploadmacro
if [ -f setup.py ]; then
    python setup.py bdist_egg > /dev/null 2>&1
    cp dist/*.egg ../../docker/trac/plugins/ 2>/dev/null || true
    print_status "Built PDF upload plugin"
else
    print_warning "No plugin to build"
fi
cd ../..

# Step 4: Stop any existing containers
echo ""
echo "Step 4: Cleaning up existing containers..."

docker compose -f docker-compose.aws-v3.yml down 2>/dev/null || true
docker compose -f docker-compose.aws-v2.yml down 2>/dev/null || true
docker compose -f docker-compose.aws.yml down 2>/dev/null || true
docker compose -f docker-compose.local.yml down 2>/dev/null || true
docker compose down 2>/dev/null || true

print_status "Cleaned up existing containers"

# Step 5: Start containers
echo ""
echo "Step 5: Starting containers..."

docker compose -f docker-compose.aws-v3.yml up -d --build

# Wait for services
echo ""
echo "Waiting for services to start..."
sleep 10

# Step 6: Check service health
echo ""
echo "Step 6: Checking service health..."

# Check Trac
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 | grep -q "200\|301\|302"; then
    print_status "Trac is running at http://localhost:8000"
else
    print_error "Trac is not responding"
fi

# Check Learning API
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    print_status "Learning API is running at http://localhost:8001"
else
    print_error "Learning API is not responding"
fi

# Step 7: Test database connection
echo ""
echo "Step 7: Testing AWS RDS connection..."

docker exec trac-aws python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port=5432,
        database='${DB_NAME}',
        user='${DB_USERNAME}',
        password='${DB_PASSWORD}'
    )
    print('✓ Successfully connected to AWS RDS')
    conn.close()
except Exception as e:
    print('✗ Failed to connect to AWS RDS:', str(e))
" || print_warning "Could not test database connection"

# Step 8: Test Neo4j connection
echo ""
echo "Step 8: Testing Neo4j connection..."

# Test Neo4j connectivity through the API
NEO4J_STATUS=$(curl -s http://localhost:8001/api/trac/neo4j/status 2>/dev/null || echo "{}")

if echo "$NEO4J_STATUS" | grep -q '"connected":true'; then
    print_status "Successfully connected to Neo4j"
    
    # Extract stats if available
    TEXTBOOK_COUNT=$(echo "$NEO4J_STATUS" | jq -r '.stats.textbooks // 0')
    CHUNK_COUNT=$(echo "$NEO4J_STATUS" | jq -r '.stats.chunks // 0')
    CONCEPT_COUNT=$(echo "$NEO4J_STATUS" | jq -r '.stats.concepts // 0')
    
    if [ "$TEXTBOOK_COUNT" != "0" ] || [ "$CHUNK_COUNT" != "0" ] || [ "$CONCEPT_COUNT" != "0" ]; then
        echo "   📚 Textbooks: $TEXTBOOK_COUNT"
        echo "   📄 Chunks: $CHUNK_COUNT"
        echo "   🧠 Concepts: $CONCEPT_COUNT"
    fi
else
    if [ -z "$NEO4J_URI" ]; then
        print_warning "Neo4j not configured - using mock data"
    else
        print_error "Failed to connect to Neo4j"
        echo "$NEO4J_STATUS" | jq '.' 2>/dev/null || echo "$NEO4J_STATUS"
    fi
fi

# Final summary
echo ""
echo "================================================"
echo "LearnTrac is running!"
echo "================================================"
echo ""
echo "🌐 Access URLs:"
echo "   Trac Wiki: http://localhost:8000"
echo "   Learning API: http://localhost:8001"
echo ""
echo "📝 Test the Wiki Macros:"
echo "   1. Go to http://localhost:8000/wiki"
echo "   2. Create a new page"
echo "   3. Add these macros:"
echo "      [[PDFUpload]]"
echo "      [[TextbookList]]"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:    docker compose -f docker-compose.aws-v3.yml logs -f"
echo "   Stop:         docker compose -f docker-compose.aws-v3.yml down"
echo "   Restart:      docker compose -f docker-compose.aws-v3.yml restart"
echo ""
if [ ! -z "$NEO4J_URI" ] && echo "$NEO4J_STATUS" | grep -q '"connected":true'; then
    echo "✅ Connected to: AWS RDS PostgreSQL, ElastiCache Redis, Neo4j Aura"
else
    echo "✅ Connected to: AWS RDS PostgreSQL, ElastiCache Redis"
    echo "⚠️  Neo4j: Using mock data (no credentials found)"
fi
echo ""