#!/bin/bash
echo "Starting simple Trac server..."

# Create a minimal Trac environment using SQLite for testing
if [ ! -d /var/trac/projects/learntrac ]; then
    echo "Creating new Trac environment..."
    trac-admin /var/trac/projects/learntrac initenv "LearnTrac Test" sqlite:db/trac.db
fi

# Copy the plugin
echo "Copying plugin..."
mkdir -p /var/trac/projects/learntrac/plugins
cp -r /app/plugins/learntrac_display /var/trac/projects/learntrac/plugins/

# Skip plugin installation for now due to Python 2.7 compatibility issues
# echo "Installing plugin..."
# cd /app/plugins/learntrac_display && python setup.py install

# Start tracd
echo "Starting Trac on port 8000..."
exec tracd --port 8000 /var/trac/projects/learntrac