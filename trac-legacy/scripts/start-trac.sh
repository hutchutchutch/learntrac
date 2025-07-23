#!/bin/bash

# Exit on error
set -e

echo "Starting Trac initialization..."

# Initialize Trac environment if it doesn't exist
if [ ! -f "/var/trac/projects/VERSION" ]; then
    echo "Initializing Trac environment..."
    trac-admin /var/trac/projects initenv "LearnTrac" "${DATABASE_URL}" git /var/git/repos
fi

# Upgrade Trac database
echo "Upgrading Trac database..."
trac-admin /var/trac/projects upgrade

# Deploy static resources
echo "Deploying static resources..."
trac-admin /var/trac/projects deploy /tmp/deploy

# Create htpasswd file if AUTH_HTPASSWD is provided
if [ ! -z "$AUTH_HTPASSWD" ]; then
    echo "$AUTH_HTPASSWD" > /etc/trac/htpasswd
fi

# Start Trac using the standalone server
echo "Starting Trac server on port 8000..."
exec tracd --port 8000 \
    --auth="*,/etc/trac/htpasswd,LearnTrac" \
    /var/trac/projects