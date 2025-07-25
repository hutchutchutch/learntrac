# Terraform Apply Guide for LearnTrac Infrastructure

## Overview

This guide provides instructions for safely applying Terraform changes to the LearnTrac infrastructure. The current plan includes:

- **51 resources to create**
- **1 resource to modify**
- **0 resources to destroy**

## Prerequisites

1. **AWS Credentials**: Ensure your AWS credentials are configured:
   ```bash
   aws sts get-caller-identity
   ```

2. **Terraform Version**: Verify you have Terraform >= 1.0:
   ```bash
   terraform version
   ```

3. **State Backup**: The current state is already backed up at `terraform.tfstate.backup`

## Apply Options

### Option 1: Simple Apply (Development)

For development environments, use the simple apply script:

```bash
./scripts/apply-terraform-simple.sh
```

This script will:
- Initialize Terraform
- Create a plan
- Show a summary
- Apply changes after confirmation

### Option 2: Staged Apply (Production)

For production or when you want more control:

```bash
./scripts/apply-terraform-staged.sh
```

This script applies changes in stages:
1. Security groups and network configurations
2. Database enhancements (parameter groups, monitoring)
3. Lambda and Cognito updates
4. API Gateway resources
5. Monitoring and dashboards
6. All remaining resources

### Option 3: Manual Apply

For complete control:

```bash
# Review the plan
terraform plan

# Apply specific targets first (optional)
terraform apply -target=aws_security_group.rds_enhanced

# Apply everything
terraform apply
```

## Post-Apply Validation

After applying changes, run the validation script:

```bash
./scripts/validate-infrastructure.sh
```

This will check:
- Terraform state resources
- AWS resource accessibility
- Security groups
- IAM roles
- Secrets Manager entries

## Expected Resources

### API Gateway Components
- API deployment and stage
- Methods for courses and authentication endpoints
- CORS configuration
- Usage plans with rate limiting

### Security Enhancements
- Enhanced security groups for RDS, Lambda, and ECS
- KMS encryption key for RDS
- CloudWatch log groups
- Enhanced IAM policies

### Database Improvements
- RDS parameter group for PostgreSQL 15
- RDS option group
- Enhanced monitoring configuration
- Automated backup settings

### Monitoring Infrastructure
- CloudWatch dashboard
- CloudWatch alarms
- SNS topic for alerts (production)
- API Gateway logging

## Important Notes

1. **API Gateway URL**: After apply, the API Gateway URL will be available in outputs:
   ```bash
   terraform output api_gateway_url
   ```

2. **Database Endpoint**: The RDS endpoint remains the same if the database already exists:
   ```bash
   terraform output db_endpoint
   ```

3. **Secrets**: All sensitive values are stored in AWS Secrets Manager

## Troubleshooting

### If Apply Fails

1. **Check the error message** - Terraform provides detailed error information

2. **Review the state**:
   ```bash
   terraform state list
   terraform state show <resource>
   ```

3. **Partial rollback** (if needed):
   ```bash
   terraform destroy -target=<problematic_resource>
   ```

4. **Full rollback** (last resort):
   ```bash
   cp terraform.tfstate.backup terraform.tfstate
   terraform refresh
   ```

### Common Issues

1. **API Gateway Deployment**: If the deployment fails, check that all API resources are properly configured

2. **Security Group Rules**: Ensure the referenced security groups exist

3. **IAM Permissions**: Verify your AWS credentials have sufficient permissions

## Next Steps After Apply

1. **Test API Endpoints**:
   ```bash
   curl -X GET $(terraform output -raw api_gateway_url)/api/v1/courses
   ```

2. **Verify Database Connectivity**:
   ```bash
   psql -h $(terraform output -raw db_endpoint | cut -d: -f1) -U learntrac_admin -d learntrac
   ```

3. **Check CloudWatch Dashboards**: Log into AWS Console and verify dashboards are populated

4. **Update Application Configuration**: Use the outputs to configure your application:
   ```bash
   terraform output -json > ../app-config.json
   ```

## Emergency Contacts

- **Infrastructure Lead**: hutch (hutchenbach@gmail.com)
- **AWS Account**: 971422717446
- **Region**: us-east-2

## Files Created

- `TERRAFORM_APPLY_PLAN.md` - Detailed apply plan
- `scripts/apply-terraform-staged.sh` - Staged apply script
- `scripts/apply-terraform-simple.sh` - Simple apply script
- `scripts/validate-infrastructure.sh` - Validation script
- `terraform-outputs.json` - Will be created after apply

---

Remember: Always review the plan before applying, especially in production environments!