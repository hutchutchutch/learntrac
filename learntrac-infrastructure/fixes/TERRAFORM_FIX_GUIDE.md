# Terraform Apply Error Fix Guide

This guide addresses the three main errors encountered during `terraform apply`:

## Error 1: API Gateway Stage Already Exists

**Error Message:**
```
Error: creating API Gateway Stage (dev): operation error API Gateway: CreateStage, 
ConflictException: Stage already exists
```

**Root Cause:**
- The `aws_api_gateway_deployment` resource uses the deprecated `stage_name` parameter
- This creates a stage automatically
- The separate `aws_api_gateway_stage` resource then tries to create the same stage

**Solution:**

1. Import the existing stage:
```bash
terraform import aws_api_gateway_stage.learntrac_stage 42ravkacea/dev
```

2. Remove `stage_name` from the deployment resource in `api-gateway-enhanced.tf`:
```hcl
resource "aws_api_gateway_deployment" "learntrac_api" {
  rest_api_id = aws_api_gateway_rest_api.learntrac_api.id
  # stage_name  = var.environment  # Remove this line
  
  # ... rest of configuration
}
```

## Error 2: RDS Parameter Group - Invalid Apply Method

**Error Message:**
```
Error: modifying RDS DB Parameter Group: InvalidParameterCombination: 
cannot use immediate apply method for static parameter
```

**Root Cause:**
- Some PostgreSQL parameters are "static" and require a database reboot
- The configuration incorrectly uses `apply_method = "immediate"` for all parameters

**Solution:**

Update the parameter group to use correct apply methods:

```hcl
# Static parameters that require reboot
parameter {
  name         = "shared_buffers"
  value        = "{DBInstanceClassMemory/4}"
  apply_method = "pending-reboot"  # Changed from "immediate"
}

parameter {
  name         = "shared_preload_libraries"
  value        = "pg_stat_statements"
  apply_method = "pending-reboot"  # Changed from "immediate"
}

# Dynamic parameters can use immediate
parameter {
  name         = "work_mem"
  value        = "4096"
  apply_method = "immediate"  # This is OK
}
```

**Note:** After applying, the RDS instance will need a reboot for static parameters to take effect.

## Error 3: Duplicate Security Group Rule

**Error Message:**
```
Error: A duplicate Security Group rule was found on (sg-0456074f9f3016cdf). 
InvalidPermission.Duplicate: the specified rule already exists
```

**Root Cause:**
- Both `module.trac_service` and `module.learntrac_service` are using the same security group ID
- The configuration tries to create two identical rules

**Solution Options:**

### Option A: Remove the duplicate rule (if both services use the same SG)
```bash
# Check if rules already exist
terraform state list | grep aws_security_group_rule.rds_from_ecs

# Remove the duplicate from state
terraform state rm aws_security_group_rule.rds_from_ecs_trac
```

### Option B: Use conditional creation
```hcl
locals {
  trac_sg_id      = module.trac_service.security_group_id
  learntrac_sg_id = module.learntrac_service.security_group_id
  same_sg         = local.trac_sg_id == local.learntrac_sg_id
}

# Only create if different security groups
resource "aws_security_group_rule" "rds_from_ecs_trac" {
  count = local.same_sg ? 0 : 1
  # ... rest of configuration
}
```

## Quick Fix Script

Run the provided fix script:
```bash
chmod +x fixes/apply-fixes.sh
./fixes/apply-fixes.sh
```

## Manual Fix Steps

1. **Import API Gateway Stage:**
   ```bash
   terraform import aws_api_gateway_stage.learntrac_stage 42ravkacea/dev
   ```

2. **Update Files:**
   - Edit `api-gateway-enhanced.tf` - remove `stage_name` from deployment
   - Edit `rds-enhanced.tf` - update parameter apply methods
   - Edit `security-updates.tf` - handle duplicate rules

3. **Clean Up State (if needed):**
   ```bash
   # If security group rule duplicate persists
   terraform state rm aws_security_group_rule.rds_from_ecs_trac
   ```

4. **Apply Changes:**
   ```bash
   terraform plan
   terraform apply
   ```

5. **Post-Apply Actions:**
   - Monitor RDS for pending parameter changes
   - Reboot RDS instance if required for static parameters

## Verification

After fixes are applied:

1. Check API Gateway:
   ```bash
   aws apigateway get-stage --rest-api-id 42ravkacea --stage-name dev
   ```

2. Check RDS Parameter Group:
   ```bash
   aws rds describe-db-parameters --db-parameter-group-name hutch-learntrac-dev-pg15-params
   ```

3. Check Security Groups:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-0456074f9f3016cdf
   ```

## Prevention

To prevent these issues in the future:

1. Always use `terraform plan` before `apply`
2. Keep Terraform and AWS provider versions updated
3. Use `terraform import` for existing resources
4. Test infrastructure changes in a dev environment first
5. Use proper parameter apply methods for RDS
6. Check for resource conflicts before creating rules