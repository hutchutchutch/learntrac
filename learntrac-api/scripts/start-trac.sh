#!/bin/bash
# Startup script for Trac container

set -e

echo "Starting Trac container initialization..."

# Wait for database to be ready
echo "Waiting for database..."
until python2 -c "
import psycopg2
import os
import time
max_attempts = 30
attempt = 0
while attempt < max_attempts:
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL', ''))
        conn.close()
        print('Database is ready')
        exit(0)
    except:
        attempt += 1
        time.sleep(2)
exit(1)
"; do
    echo "Database not ready, retrying..."
    sleep 2
done

# Run Trac database upgrade if needed
echo "Running Trac database upgrade..."
trac-admin /var/trac/projects/learntrac upgrade || true

# Deploy plugins
echo "Deploying Trac plugins..."
trac-admin /var/trac/projects/learntrac deploy /var/trac/projects/learntrac/htdocs

# Set permissions
echo "Setting file permissions..."
chown -R www-data:www-data /var/trac/projects/learntrac
chmod -R 755 /var/trac/projects/learntrac

# Create log directory
mkdir -p /var/log/trac
chown www-data:www-data /var/log/trac

# Start Apache
echo "Starting Apache web server..."
apache2ctl -D FOREGROUND