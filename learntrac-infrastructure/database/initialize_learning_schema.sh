#!/bin/bash

# Learning Schema Initialization Script
# This script initializes the learning schema in the LearnTrac PostgreSQL database

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/trac_db_config.ini"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    print_error "Please ensure trac_db_config.ini exists with database connection details"
    exit 1
fi

# Parse configuration
DB_HOST=$(grep -E "^host\s*=" "$CONFIG_FILE" | cut -d'=' -f2 | xargs)
DB_PORT=$(grep -E "^port\s*=" "$CONFIG_FILE" | cut -d'=' -f2 | xargs)
DB_NAME=$(grep -E "^database\s*=" "$CONFIG_FILE" | cut -d'=' -f2 | xargs)
DB_USER=$(grep -E "^user\s*=" "$CONFIG_FILE" | cut -d'=' -f2 | xargs)
DB_PASS=$(grep -E "^password\s*=" "$CONFIG_FILE" | cut -d'=' -f2 | xargs)

# Validate configuration
if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    print_error "Invalid configuration in $CONFIG_FILE"
    print_error "Required fields: host, port, database, user, password"
    exit 1
fi

# Export for psql
export PGPASSWORD="$DB_PASS"

print_status "Learning Schema Initialization Starting"
print_status "Database: $DB_NAME on $DB_HOST:$DB_PORT"

# Function to execute SQL file
execute_sql() {
    local sql_file=$1
    local description=$2
    
    if [ ! -f "$sql_file" ]; then
        print_error "SQL file not found: $sql_file"
        return 1
    fi
    
    print_status "Executing: $description"
    
    if psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -f "$sql_file" -v ON_ERROR_STOP=1; then
        print_status "✓ $description completed successfully"
        return 0
    else
        print_error "✗ $description failed"
        return 1
    fi
}

# Main execution
main() {
    # Check if learning schema already exists
    print_status "Checking if learning schema exists..."
    
    SCHEMA_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -tAc \
        "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning');")
    
    if [ "$SCHEMA_EXISTS" = "t" ]; then
        print_warning "Learning schema already exists"
        read -p "Do you want to run the migration script instead? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            execute_sql "${SCRIPT_DIR}/05_learning_schema_migrate.sql" "Learning Schema Migration"
        else
            read -p "Do you want to rollback and reinitialize? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                execute_sql "${SCRIPT_DIR}/06_learning_schema_rollback.sql" "Learning Schema Rollback"
                execute_sql "${SCRIPT_DIR}/04_learning_schema_init.sql" "Learning Schema Initialization"
            else
                print_status "Skipping initialization"
            fi
        fi
    else
        # Initialize learning schema
        execute_sql "${SCRIPT_DIR}/04_learning_schema_init.sql" "Learning Schema Initialization"
    fi
    
    # Always run validation
    print_status "Running validation..."
    execute_sql "${SCRIPT_DIR}/07_validate_learning_schema.sql" "Learning Schema Validation"
    
    # Test connection and basic operations
    print_status "Testing learning schema..."
    
    TEST_RESULT=$(psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" -tAc \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'learning';")
    
    if [ "$TEST_RESULT" -ge 7 ]; then
        print_status "✓ Learning schema initialized successfully with $TEST_RESULT tables"
    else
        print_error "✗ Learning schema initialization may have issues. Found only $TEST_RESULT tables"
        exit 1
    fi
    
    # Display summary
    echo
    print_status "=== Learning Schema Summary ==="
    psql -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" <<EOF
SELECT 'Tables' as object_type, COUNT(*) as count 
FROM information_schema.tables 
WHERE table_schema = 'learning'
UNION ALL
SELECT 'Indexes', COUNT(*) 
FROM pg_indexes 
WHERE schemaname = 'learning'
UNION ALL
SELECT 'Foreign Keys', COUNT(*)
FROM information_schema.table_constraints
WHERE table_schema = 'learning' AND constraint_type = 'FOREIGN KEY'
UNION ALL
SELECT 'Triggers', COUNT(*)
FROM information_schema.triggers
WHERE trigger_schema = 'learning';
EOF

    print_status "Learning schema initialization complete!"
}

# Execute main function
main

# Clean up
unset PGPASSWORD