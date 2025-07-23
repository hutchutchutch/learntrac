#!/bin/bash
set -e

echo "Starting Trac..."

# Initialize Trac environment if it doesn't exist
if [ ! -f /var/trac/projects/VERSION ]; then
    echo "Initializing new Trac environment..."
    python /usr/local/bin/init-trac.py
fi

# Copy Cognito plugin to Trac plugins directory
echo "Installing Cognito auth plugin..."
cp /app/plugins/cognito_auth.py /var/trac/projects/plugins/

# Set Python path to include plugins
export PYTHONPATH="/app/plugins:$PYTHONPATH"

# Start Trac using tracd (simpler than gunicorn for testing)
exec tracd --port 8000 /var/trac/projects