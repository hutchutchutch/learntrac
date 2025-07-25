#!/bin/bash
# Simple Terraform Apply Script for LearnTrac Infrastructure
# Use this for development environments or when you want a straightforward apply

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}LearnTrac Infrastructure - Terraform Apply${NC}"
echo "================================================"

# Check if we're in the right directory
if [ ! -f "main.tf" ]; then
    echo -e "${RED}Error: This script must be run from the terraform directory${NC}"
    exit 1
fi

# Initialize Terraform
echo -e "${GREEN}Initializing Terraform...${NC}"
terraform init -upgrade

# Create a plan
echo -e "${GREEN}Creating Terraform plan...${NC}"
terraform plan -out=terraform.tfplan

# Show plan summary
echo -e "${YELLOW}Plan Summary:${NC}"
terraform show -no-color terraform.tfplan | grep -E "Plan:|will be"

# Ask for confirmation
read -p "Do you want to apply this plan? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Apply cancelled${NC}"
    exit 0
fi

# Apply the plan
echo -e "${GREEN}Applying Terraform plan...${NC}"
terraform apply terraform.tfplan

# Generate outputs
echo -e "${GREEN}Saving outputs...${NC}"
terraform output -json > terraform-outputs.json

echo -e "${GREEN}Apply completed successfully!${NC}"
echo
echo "Next steps:"
echo "1. Review terraform-outputs.json for resource details"
echo "2. Test the deployed infrastructure"
echo "3. Update application configuration"