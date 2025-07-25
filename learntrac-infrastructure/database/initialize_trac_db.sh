#!/bin/bash

# Trac Database Initialization Script
# This script initializes the Trac database schema on RDS PostgreSQL

set -e

# Configuration
DB_HOST="${DB_HOST:-hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-learntrac}"
DB_USER="${DB_USER:-tracadmin}"
DB_PASSWORD="${DB_PASSWORD}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if password is provided
if [ -z "$DB_PASSWORD" ]; then
    print_error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
fi

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    print_error "psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Export password for psql
export PGPASSWORD="$DB_PASSWORD"

print_status "Starting Trac database initialization..."
print_status "Database Host: $DB_HOST"
print_status "Database Name: $DB_NAME"
print_status "Database User: $DB_USER"

# Test database connection
print_status "Testing database connection..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    print_status "Database connection successful!"
else
    print_error "Failed to connect to database. Please check your credentials."
    exit 1
fi

# Execute initialization scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize schema
print_status "Creating Trac schema and tables..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/01_trac_schema_init.sql"; then
    print_status "Schema initialization completed successfully!"
else
    print_error "Schema initialization failed!"
    exit 1
fi

# Initialize permissions
print_status "Setting up permissions and default data..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/02_trac_permissions_init.sql"; then
    print_status "Permissions initialization completed successfully!"
else
    print_error "Permissions initialization failed!"
    exit 1
fi

# Validate schema
print_status "Validating database schema..."
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCRIPT_DIR/03_validate_schema.sql"; then
    print_status "Schema validation completed!"
else
    print_warning "Schema validation had issues. Please review the output above."
fi

# Clear password from environment
unset PGPASSWORD

print_status "Trac database initialization completed!"
print_status ""
print_status "Next steps:"
print_status "1. Review the validation output above"
print_status "2. Update Trac configuration file with database connection details"
print_status "3. Test Trac application connectivity"
print_status ""
print_warning "IMPORTANT: Change the admin password after first login!"

exit 0