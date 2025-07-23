#!/bin/bash

# Script to set up secrets for LearnTrac deployment
# This script helps you configure sensitive values without committing them to git

set -e

echo "==================================="
echo "LearnTrac Secrets Configuration"
echo "==================================="
echo ""
echo "This script will help you set up sensitive configuration values."
echo "These values will be stored in terraform.tfvars (which should be in .gitignore)"
echo ""

# Check if terraform.tfvars already exists
if [ -f "learntrac-infrastructure/terraform.tfvars" ]; then
    echo "WARNING: terraform.tfvars already exists."
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting without changes."
        exit 0
    fi
fi

# Get current IP address
CURRENT_IP=$(curl -s https://api.ipify.org || echo "")
echo "Your current IP address appears to be: $CURRENT_IP"
read -p "Use this IP for database access? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    read -p "Enter your IP address: " ALLOWED_IP
else
    ALLOWED_IP=$CURRENT_IP
fi

# Neo4j configuration
echo ""
echo "Neo4j Configuration"
echo "==================="
read -p "Enter your Neo4j URI (e.g., neo4j+s://xxxx.databases.neo4j.io): " NEO4J_URI
read -p "Enter your Neo4j username [neo4j]: " NEO4J_USER
NEO4J_USER=${NEO4J_USER:-neo4j}
read -s -p "Enter your Neo4j password: " NEO4J_PASSWORD
echo

# OpenAI configuration (optional)
echo ""
echo ""
echo "OpenAI Configuration (optional)"
echo "==============================="
read -p "Do you have an OpenAI API key? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -s -p "Enter your OpenAI API key: " OPENAI_KEY
    echo
else
    OPENAI_KEY=""
fi

# Write to terraform.tfvars
cat > learntrac-infrastructure/terraform.tfvars <<EOF
# AWS Configuration
aws_region   = "us-east-2"
project_name = "learntrac"
environment  = "dev"
allowed_ip   = "$ALLOWED_IP"

# Neo4j Configuration
neo4j_uri      = "$NEO4J_URI"
neo4j_username = "$NEO4J_USER"
neo4j_password = "$NEO4J_PASSWORD"

# OpenAI Configuration
openai_api_key = "$OPENAI_KEY"
EOF

echo ""
echo "Configuration saved to learntrac-infrastructure/terraform.tfvars"
echo ""
echo "IMPORTANT: This file contains sensitive information."
echo "Make sure it's listed in .gitignore and never commit it to git!"
echo ""

# Create .env file for local development
echo "Creating .env file for local development..."
cat > learntrac-api/.env <<EOF
# Database
DATABASE_URL=postgresql://postgres:localpass@localhost:5432/learntrac

# Redis
REDIS_URL=redis://localhost:6379

# Neo4j
NEO4J_URI=$NEO4J_URI
NEO4J_USER=$NEO4J_USER
NEO4J_PASSWORD=$NEO4J_PASSWORD

# AWS
AWS_REGION=us-east-2

# OpenAI
OPENAI_API_KEY=$OPENAI_KEY
EOF

echo ".env file created for local development"
echo ""
echo "Setup complete! You can now run:"
echo "  cd learntrac-infrastructure"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"