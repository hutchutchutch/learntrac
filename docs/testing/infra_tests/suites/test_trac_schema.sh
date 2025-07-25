#!/bin/bash
# Test Script: Verify Trac 1.4.4 Database Schema (Subtask 1.6)

# Source common utilities and config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"
source "${SCRIPT_DIR}/../utils/common.sh"

# Test Suite Information
TEST_SUITE="Trac Schema Validation"
TEST_DESCRIPTION="Verify Trac 1.4.4 database schema is properly initialized"

# Start test suite
start_test_suite "$TEST_SUITE"

# Test 1: Connect to RDS and verify database exists
run_test "RDS Database Connectivity" "
    # Get RDS credentials from Secrets Manager
    if [ -n \"\$RDS_SECRET_ARN\" ]; then
        SECRET_JSON=\$(aws secretsmanager get-secret-value --secret-id \"\$RDS_SECRET_ARN\" --query SecretString --output text)
        export PGPASSWORD=\$(echo \"\$SECRET_JSON\" | jq -r .password)
        export PGUSER=\$(echo \"\$SECRET_JSON\" | jq -r .username)
    fi
    
    # Extract host and port from endpoint
    RDS_HOST=\$(echo \"\$RDS_ENDPOINT\" | cut -d: -f1)
    RDS_PORT=\$(echo \"\$RDS_ENDPOINT\" | cut -d: -f2)
    
    # Test connection
    PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -c 'SELECT version()' | grep -q 'PostgreSQL 15'
"

# Test 2: Verify all Trac tables exist
run_test "Trac Tables Existence" "
    # Check if all required Trac tables exist
    TABLES_TO_CHECK='attachment auth_cookie cache component enum milestone node_change notify permission report repository revision session session_attribute system ticket ticket_change ticket_custom version wiki'
    
    for table in \$TABLES_TO_CHECK; do
        echo \"Checking table: \$table\"
        PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='\$table'\" | grep -q 1 || exit 1
    done
"

# Test 3: Verify Trac system table has version info
run_test "Trac Version Information" "
    # Check Trac version in system table
    VERSION=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT value FROM system WHERE name='database_version'\")
    echo \"Trac database version: \$VERSION\"
    [ -n \"\$VERSION\" ] && [ \"\$VERSION\" -gt 0 ]
"

# Test 4: Verify initial permissions exist
run_test "Trac Permissions Setup" "
    # Check if basic permissions are set up
    PERM_COUNT=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT COUNT(*) FROM permission\")
    echo \"Permission entries: \$PERM_COUNT\"
    [ \"\$PERM_COUNT\" -gt 0 ]
"

# Print test summary
print_test_summary