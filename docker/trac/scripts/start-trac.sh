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

# For now, use tracd with better options to avoid the WSGI issues
exec tracd \
    --port 8000 \
    --hostname 0.0.0.0 \
    --single-env \
    --base-path / \
    /var/trac/projects