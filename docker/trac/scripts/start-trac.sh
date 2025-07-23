#!/bin/bash
set -e

echo "Starting Trac..."

# Initialize Trac environment if it doesn't exist
if [ ! -f /var/trac/projects/VERSION ]; then
    echo "Initializing new Trac environment..."
    python /usr/local/bin/init-trac.py
fi

# Start Trac using tracd (simpler than gunicorn for testing)
exec tracd --port 8000 /var/trac/projects