#!/bin/bash
set -e

# Install Trac and dependencies
pip install trac==1.4.3 PyJWT==1.7.1 cryptography==2.8

# Create Trac environment with SQLite
if [ ! -f "/var/trac/projects/VERSION" ]; then
    echo "Initializing Trac environment..."
    trac-admin /var/trac/projects initenv LearnTrac sqlite:db/trac.db
fi

# Enable Cognito auth components
cat >> /var/trac/projects/conf/trac.ini << EOF

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

[trac]
base_url = http://localhost:8000
EOF

# Install plugins
echo "Installing plugins..."
if [ -d "/plugins/cognitoauth" ]; then
    cd /plugins/cognitoauth && python setup.py bdist_egg && easy_install dist/*.egg
fi
if [ -d "/plugins/pdfuploadmacro" ]; then
    cd /plugins/pdfuploadmacro && python setup.py bdist_egg && easy_install dist/*.egg
fi

# Start Trac
echo "Starting Trac on port 8000..."
tracd --port 8000 /var/trac/projects