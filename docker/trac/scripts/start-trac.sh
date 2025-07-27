#!/bin/bash
set -e

echo "Starting Trac..."

# Initialize Trac environment if it doesn't exist
if [ ! -f /var/trac/projects/VERSION ]; then
    echo "Initializing new Trac environment..."
    python /app/scripts/init-trac.py
fi

# Set Python path to include plugins
export PYTHONPATH="/app/plugins:$PYTHONPATH"

# Create plugins directory if it doesn't exist
mkdir -p /var/trac/projects/plugins

# Note: Cognito auth plugin is now optional, using basic auth by default

# Start Trac using tracd (simpler than gunicorn for testing)
exec tracd --port 8000 /var/trac/projects