# Terraform Plan Summary - Cognito Removal

## Overview
This plan removes all AWS Cognito resources and updates the infrastructure to rely solely on the auth proxy pattern.

## Resources to be Destroyed (48 total)

### Cognito Resources
- `aws_cognito_user_pool.learntrac_users` - Main user pool
- `aws_cognito_user_pool_client.learntrac_client` - OAuth client
- `aws_cognito_user_pool_domain.learntrac_domain` - Cognito domain
- `aws_cognito_resource_server.learntrac_api` - API resource server
- `aws_cognito_user_group.admins` - Admin user group
- `aws_cognito_user_group.instructors` - Instructor user group  
- `aws_cognito_user_group.students` - Student user group

### Cognito Lambda Resources
- `aws_lambda_function.cognito_pre_token_generation` - Pre-token generation Lambda
- `aws_lambda_permission.cognito_invoke` - Lambda permission for Cognito
- `aws_iam_role.lambda_cognito` - IAM role for Cognito Lambda
- `aws_iam_role_policy.lambda_cognito_enhanced` - Enhanced IAM policy
- `aws_iam_role_policy_attachment.lambda_cognito_basic` - Basic Lambda policy
- `aws_cloudwatch_log_group.cognito_lambda_logs` - CloudWatch logs

### Cognito Configuration
- `aws_secretsmanager_secret.cognito_config` - Cognito configuration secret
- `aws_secretsmanager_secret_version.cognito_config` - Secret version
- `aws_api_gateway_authorizer.cognito` - API Gateway Cognito authorizer

### API Gateway Resources (to be replaced)
- `aws_api_gateway_rest_api.learntrac_api` → `aws_api_gateway_rest_api.learntrac`
- `aws_api_gateway_deployment.learntrac_api` → `aws_api_gateway_deployment.learntrac`
- `aws_api_gateway_stage.learntrac_stage` → `aws_api_gateway_stage.learntrac`
- `aws_cloudwatch_log_group.api_gateway_logs` → `aws_cloudwatch_log_group.api_gateway`

## Resources to be Created (88 total)

### New API Gateway Resources
- New REST API without Cognito authorizer
- New deployment and stage configurations
- New CloudWatch log groups
- API methods set to `authorization = "NONE"`

### New Lambda Resources (for LLM features)
- `aws_lambda_function.llm_generate` - Question generation
- `aws_lambda_function.llm_evaluate` - Answer evaluation
- Associated IAM roles, policies, and permissions
- CloudWatch log groups

### New Monitoring Resources
- CloudWatch dashboard
- CloudWatch alarms
- CloudWatch query definitions
- SNS topic for alerts

### New API Gateway Features
- Rate limiting configurations
- Usage plans for LLM endpoints
- API keys for rate limiting

## Resources to be Updated (3 total)
- `aws_api_gateway_usage_plan.learntrac_plan` - Update references
- `aws_secretsmanager_secret.openai_api_key` - Update configuration
- `module.learntrac_service.aws_ecs_service.main` - Remove Cognito environment variables

## Next Steps

1. **Apply the changes:**
   ```bash
   terraform apply
   ```

2. **Verify the removal:**
   - Check AWS Console to ensure Cognito resources are gone
   - Verify API Gateway no longer has Cognito authorizer
   - Confirm ECS tasks restart without Cognito environment variables

3. **Update application code:**
   - Remove Cognito SDK dependencies from learntrac-api
   - Remove JWT validation code that uses Cognito
   - Ensure auth proxy is the only authentication method

4. **Test the auth proxy flow:**
   - Login to Trac
   - Verify API calls work with session-based auth
   - Test logout functionality

## Important Notes

- The auth proxy pattern means Trac handles all authentication
- API Gateway methods now have `authorization = "NONE"` - security comes from Trac session validation
- No external JWT tokens or OAuth flows are involved
- All user authentication happens through Trac's built-in system