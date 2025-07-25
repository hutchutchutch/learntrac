#!/bin/bash
# Health check script for Trac container

# Check if Trac is responding
if curl -f -s http://localhost:8080/login > /dev/null; then
    # Check if database connection is working
    if python2 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', ''))
    conn.close()
    exit(0)
except:
    exit(1)
    " 2>/dev/null; then
        exit 0
    else
        echo "Database connection failed"
        exit 1
    fi
else
    echo "Trac HTTP check failed"
    exit 1
fi