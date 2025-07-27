#!/bin/bash
set -e

echo "================================================"
echo "Trac Initialization Script (Simplified)"
echo "================================================"

# Install dependencies
echo "Installing dependencies..."
pip install trac==1.4.3 psycopg2 || exit 1

# Create directories
mkdir -p /trac/log /trac/attachments /trac/cache /trac/chrome

# Check if already initialized
if [ -f /trac/VERSION ]; then
    echo "Using existing Trac environment"
else
    echo "Initializing new Trac environment..."
    
    # Move mounted volumes temporarily
    mv /trac/conf /tmp/conf_backup 2>/dev/null || true
    mv /trac/plugins /tmp/plugins_backup 2>/dev/null || true
    mv /trac/htdocs /tmp/htdocs_backup 2>/dev/null || true
    mv /trac/templates /tmp/templates_backup 2>/dev/null || true
    
    # Use environment variables directly
    DB_URL="postgres://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/${DB_NAME}"
    trac-admin /trac initenv learntrac "$DB_URL" || {
        echo "Failed to initialize with PostgreSQL"
        exit 1
    }
    
    # Restore mounted volumes
    rm -rf /trac/conf && mv /tmp/conf_backup /trac/conf 2>/dev/null || true
    rm -rf /trac/plugins && mv /tmp/plugins_backup /trac/plugins 2>/dev/null || true
    rm -rf /trac/htdocs && mv /tmp/htdocs_backup /trac/htdocs 2>/dev/null || true
    rm -rf /trac/templates && mv /tmp/templates_backup /trac/templates 2>/dev/null || true
fi

# Set permissions
chmod -R 777 /trac/log 2>/dev/null || true

# Start Trac
echo "Starting Trac server on port 8000..."
exec tracd --port 8000 /trac