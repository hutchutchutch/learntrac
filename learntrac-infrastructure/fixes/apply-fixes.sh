#!/bin/bash
# Script to fix Terraform apply issues

set -e

echo "=== Terraform Infrastructure Fix Script ==="
echo

# Function to backup files
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup-$(date +%Y%m%d-%H%M%S)"
        echo "✓ Backed up $file"
    fi
}

# Fix 1: Import existing API Gateway Stage
echo "=== Fix 1: Handling API Gateway Stage ==="
echo "The stage 'dev' already exists. We need to import it."
echo
echo "Run this command to import the existing stage:"
echo "terraform import aws_api_gateway_stage.learntrac_stage 42ravkacea/dev"
echo
read -p "Press enter after running the import command..."

# Fix 2: Update API Gateway deployment
echo
echo "=== Fix 2: Updating API Gateway Deployment ==="
backup_file "api-gateway-enhanced.tf"

# Remove stage_name from deployment
sed -i.tmp '14s/stage_name  = var.environment/# stage_name removed - managed by aws_api_gateway_stage/' api-gateway-enhanced.tf
rm -f api-gateway-enhanced.tf.tmp
echo "✓ Removed deprecated stage_name from API Gateway deployment"

# Fix 3: Update RDS Parameter Group
echo
echo "=== Fix 3: Fixing RDS Parameter Group ==="
backup_file "rds-enhanced.tf"

# Copy the fixed parameter group configuration
cp fixes/rds-parameter-group-fix.tf rds-parameter-group-temp.tf

# Extract the parameter group resource and replace it
awk '/^resource "aws_db_parameter_group" "learntrac_pg15"/{p=1} p&&/^}$/{print; p=0; next} !p' rds-enhanced.tf > rds-enhanced-new.tf
awk '/^resource "aws_db_parameter_group" "learntrac_pg15"/{p=1} p&&/^}$/{p=0; next} p' fixes/rds-parameter-group-fix.tf >> rds-enhanced-new.tf
awk '/^resource "aws_db_parameter_group" "learntrac_pg15"/{p=1} p&&/^}$/{p=0; next} !p&&NR>1' rds-enhanced.tf >> rds-enhanced-new.tf

mv rds-enhanced-new.tf rds-enhanced.tf
rm -f rds-parameter-group-temp.tf
echo "✓ Fixed RDS parameter group apply methods"

# Fix 4: Handle duplicate security group rules
echo
echo "=== Fix 4: Fixing Security Group Rules ==="
backup_file "security-updates.tf"

# First, let's check if the security groups are the same
TRAC_SG=$(terraform output -raw module.trac_service.security_group_id 2>/dev/null || echo "")
LEARNTRAC_SG=$(terraform output -raw module.learntrac_service.security_group_id 2>/dev/null || echo "")

if [ "$TRAC_SG" = "$LEARNTRAC_SG" ]; then
    echo "✓ Both services use the same security group: $TRAC_SG"
    echo "  Removing duplicate rule..."
    
    # Comment out the duplicate rule
    sed -i.tmp '/resource "aws_security_group_rule" "rds_from_ecs_trac"/,/^}$/s/^/# /' security-updates.tf
    rm -f security-updates.tf.tmp
    echo "✓ Commented out duplicate security group rule"
else
    echo "✓ Services use different security groups"
    echo "  You may need to remove the existing rule first:"
    echo "  terraform state rm aws_security_group_rule.rds_from_ecs_trac"
fi

echo
echo "=== Fix Summary ==="
echo "1. API Gateway stage import command provided"
echo "2. Removed deprecated stage_name from deployment"
echo "3. Fixed RDS parameter group apply methods"
echo "4. Handled duplicate security group rules"
echo
echo "Next steps:"
echo "1. Review the changes"
echo "2. Run: terraform plan"
echo "3. If plan looks good, run: terraform apply"
echo
echo "If you still see errors:"
echo "- For API Gateway: terraform import aws_api_gateway_stage.learntrac_stage 42ravkacea/dev"
echo "- For Security Groups: terraform state rm aws_security_group_rule.rds_from_ecs_trac"
echo "- For Parameter Group: The DB instance may need a reboot after apply"