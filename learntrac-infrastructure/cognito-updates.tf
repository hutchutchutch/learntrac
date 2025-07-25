# Additional Cognito configuration updates for enhanced JWT and security

# Note: MFA configuration is part of the user pool resource itself
# Custom attributes must be defined in the user pool schema

# Add identity provider configuration for future OAuth integrations
resource "aws_cognito_identity_provider" "google" {
  count        = var.enable_google_oauth ? 1 : 0
  user_pool_id = aws_cognito_user_pool.learntrac_users.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "email openid profile"
  }

  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }
}

# Add CloudWatch log group for Cognito Lambda
resource "aws_cloudwatch_log_group" "cognito_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cognito_pre_token_generation.function_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-cognito-lambda-logs"
  })
}

# Enhanced IAM policy for Lambda to access additional AWS services
resource "aws_iam_role_policy" "lambda_cognito_enhanced" {
  name = "${local.project_prefix}-lambda-cognito-enhanced"
  role = aws_iam_role.lambda_cognito.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn,
          aws_secretsmanager_secret.cognito_config.arn
        ]
      }
    ]
  })
}

# Data source for AWS account ID
data "aws_caller_identity" "current" {}

# Output additional JWT configuration details
output "cognito_jwt_issuer" {
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.learntrac_users.id}"
  description = "JWT issuer URL for token validation"
}

output "cognito_jwks_uri" {
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.learntrac_users.id}/.well-known/jwks.json"
  description = "JWKS URI for JWT signature verification"
}

output "cognito_callback_urls" {
  value       = aws_cognito_user_pool_client.learntrac_client.callback_urls
  description = "Configured callback URLs for OAuth flows"
}

output "cognito_logout_urls" {
  value       = aws_cognito_user_pool_client.learntrac_client.logout_urls
  description = "Configured logout URLs"
}