#!/bin/bash
set -eo pipefail

echo "================================================"
echo "Trac Initialization Script"
echo "================================================"

# Function to wait for postgres
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    until python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port=5432,
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}'
    )
    conn.close()
    print('PostgreSQL is ready!')
    exit(0)
except Exception as e:
    print(f'Waiting for PostgreSQL: {e}')
    exit(1)
" 2>/dev/null; do
        sleep 2
    done
}

# Install dependencies
echo "Installing dependencies..."
pip install --quiet trac==1.4.3 psycopg2

# Install plugin if exists
if ls /trac/plugins/PDFUploadMacro*.egg 1> /dev/null 2>&1; then
    echo "Installing PDF upload plugin..."
    easy_install /trac/plugins/PDFUploadMacro*.egg
fi

# Wait for database
wait_for_postgres

# Check if Trac environment exists
if [ ! -f /trac/VERSION ]; then
    echo "Initializing new Trac environment..."
    
    # Create directories
    mkdir -p /trac/log /trac/attachments /trac/cache /trac/chrome
    
    # Initialize Trac
    trac-admin /trac initenv learntrac "postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}" || {
        echo "Failed to initialize Trac environment"
        exit 1
    }
    
    # Set permissions
    chmod -R 777 /trac/log
    
    echo "Trac environment initialized successfully!"
else
    echo "Using existing Trac environment"
fi

# Start Trac
echo "Starting Trac server on port 8000..."
exec tracd --port 8000 /trac