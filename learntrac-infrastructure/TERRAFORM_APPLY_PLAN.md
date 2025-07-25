# Terraform Apply Plan - LearnTrac Infrastructure

## Summary

- **Resources to Add**: 51
- **Resources to Change**: 1
- **Resources to Destroy**: 0
- **Date**: July 25, 2025

## Major Components Being Created

### 1. API Gateway Resources
- API Gateway deployment and stage
- Multiple API methods (GET, OPTIONS) for CORS support
- API Gateway integrations and responses
- Usage plans with rate limiting and quotas
- CloudWatch logging for API Gateway

### 2. Security Enhancements
- KMS encryption key for RDS
- CloudWatch log groups for Lambda functions
- Enhanced IAM policies for Lambda functions
- Security group rules for database access
- WAF Web ACL for API protection (if enabled)

### 3. Database Enhancements
- RDS parameter group for PostgreSQL 15
- RDS option group
- Enhanced monitoring IAM role (for production)
- Automated backup configurations
- Performance insights settings

### 4. Monitoring and Observability
- CloudWatch dashboards
- CloudWatch alarms for various metrics
- SNS topic for alerts (production only)
- VPC Flow Logs (if enabled)

### 5. Network Security
- GuardDuty detector (if enabled)
- Security Hub integration (if enabled)
- Network ACL rules (commented out - needs fixing)

## Pre-Apply Checklist

### 1. Verify Prerequisites
- [ ] AWS credentials are configured correctly
- [ ] Terraform state is backed up
- [ ] All team members are aware of the deployment
- [ ] No critical operations are running

### 2. Review Sensitive Resources
- [ ] RDS database password is securely generated
- [ ] API keys and secrets are properly stored in Secrets Manager
- [ ] Security group rules are appropriately restrictive
- [ ] IAM policies follow least privilege principle

### 3. Cost Considerations
- [ ] RDS instance class is appropriate for workload
- [ ] ElastiCache cluster size is reasonable
- [ ] CloudWatch log retention periods are set correctly
- [ ] API Gateway usage plans have appropriate limits

## Staged Apply Process

### Stage 1: Core Security and Network
```bash
# Apply security groups and network configurations first
terraform apply -target=aws_security_group.rds_enhanced -target=aws_security_group.lambda_sg -target=aws_security_group.ecs_shared
```

### Stage 2: Database Enhancements
```bash
# Apply RDS parameter groups and monitoring
terraform apply -target=aws_db_parameter_group.learntrac_pg15 -target=aws_db_option_group.learntrac_options -target=aws_iam_role.rds_enhanced_monitoring
```

### Stage 3: API Gateway Setup
```bash
# Apply API Gateway resources
terraform apply -target=aws_api_gateway_deployment.learntrac_api -target=aws_api_gateway_stage.learntrac_stage
```

### Stage 4: Monitoring and Logging
```bash
# Apply CloudWatch resources
terraform apply -target=aws_cloudwatch_log_group.cognito_lambda_logs -target=aws_cloudwatch_dashboard.main
```

### Stage 5: Complete Apply
```bash
# Apply all remaining resources
terraform apply terraform.plan
```

## Manual Interventions Required

### 1. Post-Apply Database Tasks
- Connect to RDS instance and verify connectivity
- Run database initialization scripts if needed
- Update application configuration with new endpoints

### 2. API Gateway Configuration
- Test API endpoints after deployment
- Verify CORS settings are working correctly
- Update DNS records if using custom domain

### 3. Monitoring Setup
- Configure CloudWatch alarm notifications
- Set up alert recipients in SNS topics
- Verify dashboard metrics are populating

## Rollback Plan

If issues occur during apply:

1. **Immediate Rollback**:
   ```bash
   terraform destroy -target=<problematic_resource>
   ```

2. **State Recovery**:
   ```bash
   cp terraform.tfstate.backup terraform.tfstate
   ```

3. **Full Rollback** (if needed):
   ```bash
   terraform destroy
   ```

## Known Issues

1. **Network ACL Rules**: Currently commented out due to data source reference issues
2. **API Gateway Deprecation**: Updated to use stage URL construction instead of invoke_url
3. **Cognito MFA**: Not configured as separate resource (part of user pool)

## Next Steps

After successful apply:
1. Run integration tests
2. Update documentation with new resource IDs
3. Configure application to use new infrastructure
4. Set up monitoring alerts
5. Schedule post-deployment review

## Apply Commands

### Full Apply (Recommended for Dev)
```bash
terraform apply terraform.plan
```

### Interactive Apply (Recommended for Prod)
```bash
terraform apply
```

### Dry Run
```bash
terraform plan -detailed-exitcode
```

## Emergency Contacts

- Infrastructure Lead: hutch (hutchenbach@gmail.com)
- AWS Account Owner: hutch
- On-Call: TBD

---

**Note**: This plan was generated on July 25, 2025. Always run `terraform plan` again before applying to ensure no drift has occurred.