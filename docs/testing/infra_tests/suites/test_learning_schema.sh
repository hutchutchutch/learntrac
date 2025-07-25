#!/bin/bash
# Test Script: Verify Learning Schema (Subtask 1.7)

# Source common utilities and config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../config.sh"
source "${SCRIPT_DIR}/../utils/common.sh"

# Test Suite Information
TEST_SUITE="Learning Schema Validation"
TEST_DESCRIPTION="Verify learning schema namespace and tables are properly created"

# Start test suite
start_test_suite "$TEST_SUITE"

# Setup database connection
setup_db_connection() {
    # Get RDS credentials from Secrets Manager
    if [ -n "$RDS_SECRET_ARN" ]; then
        SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "$RDS_SECRET_ARN" --query SecretString --output text)
        export PGPASSWORD=$(echo "$SECRET_JSON" | jq -r .password)
        export PGUSER=$(echo "$SECRET_JSON" | jq -r .username)
    fi
    
    # Extract host and port from endpoint
    export RDS_HOST=$(echo "$RDS_ENDPOINT" | cut -d: -f1)
    export RDS_PORT=$(echo "$RDS_ENDPOINT" | cut -d: -f2)
}

# Test 1: Verify learning schema exists
run_test "Learning Schema Existence" "
    setup_db_connection
    
    # Check if learning schema exists
    SCHEMA_EXISTS=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT 1 FROM information_schema.schemata WHERE schema_name='learning'\")
    echo \"Schema exists check: \$SCHEMA_EXISTS\"
    [ -n \"\$SCHEMA_EXISTS\" ] && [ \"\$SCHEMA_EXISTS\" -eq 1 ]
"

# Test 2: Verify all learning tables exist
run_test "Learning Tables Structure" "
    # Check each required table in learning schema
    TABLES='paths concept_metadata prerequisites progress'
    
    for table in \$TABLES; do
        echo \"Checking table: learning.\$table\"
        TABLE_EXISTS=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT 1 FROM information_schema.tables WHERE table_schema='learning' AND table_name='\$table'\")
        [ -n \"\$TABLE_EXISTS\" ] && [ \"\$TABLE_EXISTS\" -eq 1 ] || exit 1
    done
"

# Test 3: Verify foreign key relationships to Trac
run_test "Foreign Key Constraints" "
    # Check foreign key from concept_metadata to public.ticket
    FK_EXISTS=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"
        SELECT 1 FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
        ON tc.constraint_name = ccu.constraint_name
        WHERE tc.table_schema = 'learning'
        AND tc.table_name = 'concept_metadata'
        AND tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_schema = 'public'
        AND ccu.table_name = 'ticket'
    \")
    echo \"Foreign key to ticket table: \$FK_EXISTS\"
    [ -n \"\$FK_EXISTS\" ] && [ \"\$FK_EXISTS\" -eq 1 ]
"

# Test 4: Verify UUID extension is enabled
run_test "UUID Extension" "
    # Check if gen_random_uuid function is available
    UUID_FUNC=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -tc \"SELECT 1 FROM pg_proc WHERE proname='gen_random_uuid'\")
    echo \"UUID function available: \$UUID_FUNC\"
    [ -n \"\$UUID_FUNC\" ] && [ \"\$UUID_FUNC\" -eq 1 ]
"

# Test 5: Test insert capability
run_test "Table Insert Capability" "
    # Try to insert a test learning path
    INSERT_RESULT=\$(PGPASSWORD=\$PGPASSWORD psql -h \"\$RDS_HOST\" -p \"\$RDS_PORT\" -U \"\$PGUSER\" -d \"\$RDS_DATABASE\" -c \"
        INSERT INTO learning.paths (title, query_text, cognito_user_id, question_difficulty)
        VALUES ('Test Path', 'Test Query', 'test-user-123', 3)
        RETURNING id;
    \" 2>&1)
    
    # Check if insert was successful (either new insert or unique constraint)
    echo \"\$INSERT_RESULT\" | grep -qE '(INSERT 0 1|duplicate key)'
"

# Print test summary
print_test_summary