#!/bin/bash

# Exit on error
set -e

echo "Starting Trac placeholder service..."

# For initial deployment, run a simple HTTP server
# This will be replaced with actual Trac initialization once database is configured
echo "Running placeholder Trac service on port 8000..."
cd /var/trac
echo '<!DOCTYPE html><html><head><title>Trac Service</title></head><body><h1>Trac Service</h1><p>Service is running. Full Trac initialization pending database configuration.</p></body></html>' > index.html
python -m SimpleHTTPServer 8000