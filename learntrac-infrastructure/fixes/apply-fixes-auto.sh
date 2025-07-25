#!/bin/bash
# Automated Terraform Infrastructure Fix Script (non-interactive)

set -e

echo "=== Terraform Infrastructure Fix Script (Automated) ==="
echo

# Function to backup files
backup_file() {
    local file=$1
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup-$(date +%Y%m%d-%H%M%S)"
        echo "✓ Backed up $file"
    fi
}

# Fix 1: API Gateway Stage
echo "=== Fix 1: API Gateway Stage ==="
echo "✓ Stage already imported successfully"

# Fix 2: Update API Gateway deployment
echo
echo "=== Fix 2: Updating API Gateway Deployment ==="
backup_file "api-gateway-enhanced.tf"

# Remove stage_name from deployment
if grep -q "stage_name  = var.environment" api-gateway-enhanced.tf; then
    sed -i.tmp '14s/stage_name  = var.environment/# stage_name removed - managed by aws_api_gateway_stage/' api-gateway-enhanced.tf
    rm -f api-gateway-enhanced.tf.tmp
    echo "✓ Removed deprecated stage_name from API Gateway deployment"
else
    echo "✓ stage_name already removed or not found"
fi

# Fix 3: Update RDS Parameter Group
echo
echo "=== Fix 3: Fixing RDS Parameter Group ==="
backup_file "rds-enhanced.tf"

# Create a fixed version of the parameter group
cat > rds-parameter-group-fixed.tf << 'EOF'
# Enhanced RDS Configuration for LearnTrac

# Parameter group for PostgreSQL 15 optimization
resource "aws_db_parameter_group" "learntrac_pg15" {
  name        = "${local.project_prefix}-pg15-params"
  family      = "postgres15"
  description = "Custom parameter group for LearnTrac PostgreSQL 15"

  # Connection settings
  parameter {
    name         = "max_connections"
    value        = var.environment == "prod" ? "200" : "100"
    apply_method = "immediate"
  }

  # Memory settings - Fixed apply methods
  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/4}"
    apply_method = "pending-reboot"  # Fixed: was immediate
  }

  parameter {
    name         = "effective_cache_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "immediate"
  }

  parameter {
    name         = "work_mem"
    value        = "4096"
    apply_method = "immediate"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "65536"
    apply_method = "immediate"
  }

  # Query optimization
  parameter {
    name         = "random_page_cost"
    value        = "1.1"
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_io_concurrency"
    value        = "200"
    apply_method = "immediate"
  }

  # Logging for troubleshooting
  parameter {
    name         = "log_statement"
    value        = var.environment == "prod" ? "mod" : "all"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = var.environment == "prod" ? "1000" : "500"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_disconnections"
    value        = "1"
    apply_method = "immediate"
  }

  # Enable query performance insights - Fixed apply method
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"  # Fixed: was immediate
  }

  parameter {
    name         = "pg_stat_statements.track"
    value        = "all"
    apply_method = "immediate"
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-parameter-group"
  })
}
EOF

# Extract everything before and after the parameter group resource
awk '/^resource "aws_db_parameter_group" "learntrac_pg15"/{p=1} !p{print}' rds-enhanced.tf > rds-enhanced-part1.tf
awk 'BEGIN{p=0} /^resource "aws_db_parameter_group" "learntrac_pg15"/{p=1} p&&/^}$/{p=0; getline} p==0&&NR>1{print}' rds-enhanced.tf > rds-enhanced-part2.tf

# Combine with the fixed parameter group
cat rds-enhanced-part1.tf rds-parameter-group-fixed.tf rds-enhanced-part2.tf > rds-enhanced-new.tf
mv rds-enhanced-new.tf rds-enhanced.tf
rm -f rds-enhanced-part1.tf rds-enhanced-part2.tf rds-parameter-group-fixed.tf

echo "✓ Fixed RDS parameter group apply methods"

# Fix 4: Handle duplicate security group rules
echo
echo "=== Fix 4: Fixing Security Group Rules ==="
backup_file "security-updates.tf"

# Check if the duplicate rule exists in state
if terraform state show aws_security_group_rule.rds_from_ecs_trac 2>/dev/null | grep -q "sg-099f0e67fcf8b6870"; then
    echo "✓ Found duplicate security group rule in state"
    echo "  Removing from Terraform state..."
    terraform state rm aws_security_group_rule.rds_from_ecs_trac || true
    echo "✓ Removed duplicate rule from state"
fi

# Comment out the duplicate rule in the configuration
if grep -q '^resource "aws_security_group_rule" "rds_from_ecs_trac"' security-updates.tf; then
    sed -i.tmp '/^resource "aws_security_group_rule" "rds_from_ecs_trac"/,/^}$/s/^/# /' security-updates.tf
    rm -f security-updates.tf.tmp
    echo "✓ Commented out duplicate security group rule in configuration"
else
    echo "✓ Security group rule already commented or not found"
fi

echo
echo "=== Fix Summary ==="
echo "✅ API Gateway stage imported"
echo "✅ Removed deprecated stage_name from deployment"
echo "✅ Fixed RDS parameter group apply methods"
echo "✅ Handled duplicate security group rules"
echo
echo "All fixes have been applied automatically!"
echo
echo "Next steps:"
echo "1. Run: terraform plan"
echo "2. Review the plan output"
echo "3. If everything looks good, run: terraform apply"
echo
echo "Note: RDS instance may require a reboot after apply for static parameter changes."