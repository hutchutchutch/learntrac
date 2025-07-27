#!/bin/bash
set -e

echo "==================================="
echo "Starting Trac with Cognito Auth"
echo "==================================="

# Set up environment
export TRAC_ENV="/var/trac/projects"

# Install dependencies
echo "Installing dependencies..."
pip install --quiet trac==1.4.3 PyJWT==1.7.1 cryptography==2.8 psycopg2-binary

# Create Trac environment directory
mkdir -p $TRAC_ENV

# Initialize Trac with SQLite if not exists
if [ ! -f "$TRAC_ENV/VERSION" ]; then
    echo "Initializing new Trac environment..."
    trac-admin $TRAC_ENV initenv "LearnTrac" "sqlite:db/trac.db"
fi

# Update trac.ini with Cognito settings
echo "Configuring Cognito authentication..."
cat > $TRAC_ENV/conf/trac.ini << 'EOF'
# -*- coding: utf-8 -*-

[trac]
database = sqlite:db/trac.db
base_url = http://localhost:8000

[project]
name = LearnTrac
descr = Learning Management System with Trac

[components]
# Enable Cognito authentication
cognitoauth.* = enabled
# Disable default Trac authentication
trac.web.auth.* = disabled
# Enable PDF upload plugin
pdfuploadmacro.* = enabled

[cognito]
client_id = 5adkv019v4rcu6o87ffg46ep02
domain = hutch-learntrac-dev-auth
region = us-east-2
user_pool_id = us-east-2_IvxzMrWwg
login_redirect_path = /trac/wiki

[attachment]
max_size = 262144
render_unsafe_content = false

[logging]
log_file = trac.log
log_level = DEBUG
log_type = file

[wiki]
max_size = 262144
EOF

# Install plugins
echo "Installing plugins..."
if [ -d "/plugins/cognitoauth" ]; then
    echo "Installing Cognito auth plugin..."
    cp -r /plugins/cognitoauth /tmp/
    cd /tmp/cognitoauth
    python setup.py bdist_egg
    easy_install dist/*.egg
fi

if [ -d "/plugins/pdfuploadmacro" ]; then
    echo "Installing PDF upload plugin..."
    cp -r /plugins/pdfuploadmacro /tmp/
    cd /tmp/pdfuploadmacro
    python setup.py bdist_egg
    easy_install dist/*.egg
fi

# Set permissions
chmod -R 777 $TRAC_ENV

# Start Trac
echo "Starting Trac on port 8000..."
echo "Access at: http://localhost:8000/trac"
echo "==================================="
cd /
exec tracd --port 8000 --base-path=/trac $TRAC_ENV