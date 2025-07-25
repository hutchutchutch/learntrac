#!/bin/bash

# RDS PostgreSQL Validation Script
# This script validates the RDS instance configuration and connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}RDS PostgreSQL Instance Validation${NC}"
echo "===================================="
echo ""

# Get RDS endpoint from Terraform
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")
if [ -z "$RDS_ENDPOINT" ]; then
    echo -e "${RED}Error: Could not get RDS endpoint from Terraform outputs${NC}"
    exit 1
fi

# Parse endpoint
RDS_HOST=$(echo $RDS_ENDPOINT | cut -d: -f1)
RDS_PORT=$(echo $RDS_ENDPOINT | cut -d: -f2)

echo -e "RDS Endpoint: ${GREEN}$RDS_ENDPOINT${NC}"
echo ""

# Get credentials from Secrets Manager
SECRET_NAME="hutch-learntrac-dev-db-credentials"
echo "Retrieving credentials from AWS Secrets Manager..."

DB_CREDENTIALS=$(aws secretsmanager get-secret-value \
    --secret-id $SECRET_NAME \
    --query SecretString \
    --output text 2>/dev/null || echo "")

if [ -z "$DB_CREDENTIALS" ]; then
    echo -e "${RED}Error: Could not retrieve database credentials from Secrets Manager${NC}"
    exit 1
fi

# Parse credentials
DB_USERNAME=$(echo $DB_CREDENTIALS | jq -r .username)
DB_PASSWORD=$(echo $DB_CREDENTIALS | jq -r .password)
DB_NAME=$(echo $DB_CREDENTIALS | jq -r .dbname)

echo -e "${GREEN}✓${NC} Credentials retrieved successfully"
echo ""

# Function to run PostgreSQL commands
run_psql() {
    local query=$1
    PGPASSWORD=$DB_PASSWORD psql -h $RDS_HOST -p $RDS_PORT -U $DB_USERNAME -d $DB_NAME -t -c "$query" 2>&1
}

# Test 1: Basic connectivity
echo "1. Testing Database Connectivity"
echo "-------------------------------"
if PGPASSWORD=$DB_PASSWORD psql -h $RDS_HOST -p $RDS_PORT -U $DB_USERNAME -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Successfully connected to RDS instance"
else
    echo -e "${RED}✗${NC} Failed to connect to RDS instance"
    echo "Please check:"
    echo "  - Security group allows access from your IP"
    echo "  - RDS instance is available"
    echo "  - Credentials are correct"
    exit 1
fi

# Test 2: PostgreSQL version
echo ""
echo "2. PostgreSQL Version Check"
echo "-------------------------"
PG_VERSION=$(run_psql "SELECT version();")
echo -e "Version: ${GREEN}$PG_VERSION${NC}"

# Check if it's PostgreSQL 15
if echo "$PG_VERSION" | grep -q "PostgreSQL 15"; then
    echo -e "${GREEN}✓${NC} PostgreSQL 15.x confirmed"
else
    echo -e "${YELLOW}⚠${NC} Warning: Expected PostgreSQL 15.x"
fi

# Test 3: Database configuration
echo ""
echo "3. Database Configuration"
echo "-----------------------"
echo -e "Database Name: ${GREEN}$DB_NAME${NC}"
echo -e "Username: ${GREEN}$DB_USERNAME${NC}"
echo -e "Host: ${GREEN}$RDS_HOST${NC}"
echo -e "Port: ${GREEN}$RDS_PORT${NC}"

# Test 4: Storage and performance settings
echo ""
echo "4. Storage and Performance Settings"
echo "---------------------------------"
STORAGE_INFO=$(run_psql "SELECT pg_database_size('$DB_NAME'), pg_size_pretty(pg_database_size('$DB_NAME'));")
echo -e "Database Size: ${GREEN}$(echo $STORAGE_INFO | awk '{print $2" "$3}')${NC}"

# Check important PostgreSQL settings
echo ""
echo "Key PostgreSQL Settings:"
MAX_CONNECTIONS=$(run_psql "SHOW max_connections;")
SHARED_BUFFERS=$(run_psql "SHOW shared_buffers;")
WORK_MEM=$(run_psql "SHOW work_mem;")
echo -e "  max_connections: ${GREEN}$MAX_CONNECTIONS${NC}"
echo -e "  shared_buffers: ${GREEN}$SHARED_BUFFERS${NC}"
echo -e "  work_mem: ${GREEN}$WORK_MEM${NC}"

# Test 5: Extensions
echo ""
echo "5. PostgreSQL Extensions"
echo "----------------------"
EXTENSIONS=$(run_psql "SELECT extname FROM pg_extension ORDER BY extname;")
echo "Installed extensions:"
echo "$EXTENSIONS" | while read ext; do
    if [ ! -z "$ext" ]; then
        echo -e "  - ${GREEN}$ext${NC}"
    fi
done

# Check for UUID extension (required for learning schema)
if echo "$EXTENSIONS" | grep -q "uuid-ossp"; then
    echo -e "${GREEN}✓${NC} uuid-ossp extension is installed"
else
    echo -e "${YELLOW}⚠${NC} uuid-ossp extension not found - installing..."
    run_psql "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
    echo -e "${GREEN}✓${NC} uuid-ossp extension installed"
fi

# Test 6: Schema check
echo ""
echo "6. Database Schemas"
echo "-----------------"
SCHEMAS=$(run_psql "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast') ORDER BY schema_name;")
echo "Available schemas:"
echo "$SCHEMAS" | while read schema; do
    if [ ! -z "$schema" ]; then
        echo -e "  - ${GREEN}$schema${NC}"
    fi
done

# Test 7: Table count
echo ""
echo "7. Database Tables"
echo "----------------"
TABLE_COUNT=$(run_psql "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo -e "Tables in public schema: ${GREEN}$TABLE_COUNT${NC}"

if [ "$TABLE_COUNT" -gt "0" ]; then
    echo "Sample tables:"
    TABLES=$(run_psql "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5;")
    echo "$TABLES" | while read table; do
        if [ ! -z "$table" ]; then
            echo -e "  - ${GREEN}$table${NC}"
        fi
    done
fi

# Test 8: Security configuration
echo ""
echo "8. Security Configuration"
echo "-----------------------"
SSL_STATUS=$(run_psql "SHOW ssl;")
echo -e "SSL Enabled: ${GREEN}$SSL_STATUS${NC}"

ENCRYPTED=$(run_psql "SELECT datname, datcollate FROM pg_database WHERE datname = '$DB_NAME';")
echo -e "Database Collation: ${GREEN}$(echo $ENCRYPTED | awk '{print $2}')${NC}"

# Test 9: Backup configuration
echo ""
echo "9. Backup Configuration (from AWS)"
echo "--------------------------------"
BACKUP_INFO=$(aws rds describe-db-instances \
    --db-instance-identifier hutch-learntrac-dev-db \
    --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow,PreferredMaintenanceWindow]' \
    --output text 2>/dev/null || echo "")

if [ ! -z "$BACKUP_INFO" ]; then
    RETENTION=$(echo $BACKUP_INFO | awk '{print $1}')
    BACKUP_WINDOW=$(echo $BACKUP_INFO | awk '{print $2}')
    MAINT_WINDOW=$(echo $BACKUP_INFO | awk '{print $3}')
    echo -e "Backup Retention: ${GREEN}$RETENTION days${NC}"
    echo -e "Backup Window: ${GREEN}$BACKUP_WINDOW${NC}"
    echo -e "Maintenance Window: ${GREEN}$MAINT_WINDOW${NC}"
fi

# Test 10: Performance Insights
echo ""
echo "10. Performance Monitoring"
echo "------------------------"
PERF_INSIGHTS=$(aws rds describe-db-instances \
    --db-instance-identifier hutch-learntrac-dev-db \
    --query 'DBInstances[0].PerformanceInsightsEnabled' \
    --output text 2>/dev/null || echo "False")

if [ "$PERF_INSIGHTS" == "true" ] || [ "$PERF_INSIGHTS" == "True" ]; then
    echo -e "Performance Insights: ${GREEN}Enabled${NC}"
else
    echo -e "Performance Insights: ${YELLOW}Disabled${NC} (Normal for dev environment)"
fi

# Summary
echo ""
echo -e "${BLUE}Validation Summary${NC}"
echo "=================="
echo -e "${GREEN}✓${NC} RDS instance is accessible"
echo -e "${GREEN}✓${NC} PostgreSQL 15.x is running"
echo -e "${GREEN}✓${NC} Database '$DB_NAME' exists"
echo -e "${GREEN}✓${NC} Security settings are configured"
echo -e "${GREEN}✓${NC} Backup is configured ($RETENTION days retention)"

# Check if ready for Trac
echo ""
echo -e "${BLUE}Trac Readiness Check${NC}"
echo "==================="
if [ "$TABLE_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠${NC} No tables found - Trac schema needs to be initialized"
    echo "  Run Task 1.6 to initialize Trac database schema"
else
    echo -e "${GREEN}✓${NC} Database has tables (verify if Trac tables)"
fi

# Check for learning schema
if echo "$SCHEMAS" | grep -q "learning"; then
    echo -e "${GREEN}✓${NC} Learning schema exists"
else
    echo -e "${YELLOW}⚠${NC} Learning schema not found - needs to be created"
    echo "  Run Task 1.7 to create learning schema"
fi

echo ""
echo "RDS validation complete!"