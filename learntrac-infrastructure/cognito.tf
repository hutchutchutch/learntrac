# IAM role for Lambda (defined first)
resource "aws_iam_role" "cognito_lambda" {
  name = "${local.project_prefix}-cognito-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "cognito_lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.cognito_lambda.name
}

# Lambda function for pre-token generation (defined before user pool)
resource "aws_lambda_function" "cognito_pre_token" {
  filename         = "${path.module}/lambda/cognito-pre-token.zip"
  function_name    = "${local.project_prefix}-cognito-pre-token"
  role            = aws_iam_role.cognito_lambda.arn
  handler         = "index.handler"
  runtime         = "nodejs18.x"
  timeout         = 10

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  tags = local.common_tags
}

# Cognito User Pool for LearnTrac Authentication
resource "aws_cognito_user_pool" "learntrac" {
  name = "${local.project_prefix}-users"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # User attributes
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  schema {
    attribute_data_type      = "String"
    mutable                  = true
    name                     = "email"
    required                 = true
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    attribute_data_type      = "String"
    mutable                  = true
    name                     = "name"
    required                 = true
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    attribute_data_type      = "String"
    mutable                  = true
    name                     = "role"
    required                 = false
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Lambda configuration
  lambda_config {
    pre_token_generation = aws_lambda_function.cognito_pre_token.arn
  }

  tags = local.common_tags
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "learntrac" {
  name         = "${local.project_prefix}-client"
  user_pool_id = aws_cognito_user_pool.learntrac.id

  # OAuth settings
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true
  supported_identity_providers         = ["COGNITO"]

  # Callback URLs - update these for your environment
  callback_urls = [
    "http://localhost:8000/auth/callback",
    "http://localhost:8001/auth/callback",
    "https://${aws_api_gateway_rest_api.learntrac.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.learntrac.stage_name}/auth/callback"
  ]

  logout_urls = [
    "http://localhost:8000/",
    "http://localhost:8001/",
    "https://${aws_api_gateway_rest_api.learntrac.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.learntrac.stage_name}/"
  ]

  # Token validity (in minutes)
  refresh_token_validity = 30  # days
  access_token_validity  = 60  # minutes
  id_token_validity      = 60  # minutes
  
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read attributes
  read_attributes = ["email", "name", "custom:role"]

  # Write attributes
  write_attributes = ["email", "name", "custom:role"]

  depends_on = [aws_cognito_user_pool.learntrac]
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "learntrac" {
  domain       = "${local.project_prefix}-auth"
  user_pool_id = aws_cognito_user_pool.learntrac.id
}

# User Groups
resource "aws_cognito_user_group" "admins" {
  name         = "admins"
  user_pool_id = aws_cognito_user_pool.learntrac.id
  description  = "Administrator users with full access"
  precedence   = 1
}

resource "aws_cognito_user_group" "instructors" {
  name         = "instructors"
  user_pool_id = aws_cognito_user_pool.learntrac.id
  description  = "Instructors with content management access"
  precedence   = 2
}

resource "aws_cognito_user_group" "students" {
  name         = "students"
  user_pool_id = aws_cognito_user_pool.learntrac.id
  description  = "Students with learning access"
  precedence   = 3
}


# Lambda permission for Cognito
resource "aws_lambda_permission" "cognito_trigger" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_pre_token.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.learntrac.arn
}


# Outputs
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.learntrac.id
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.learntrac.id
}

output "cognito_domain" {
  description = "Cognito domain for hosted UI"
  value       = aws_cognito_user_pool_domain.learntrac.domain
}

output "cognito_login_url" {
  description = "URL for Cognito hosted login page"
  value       = "https://${aws_cognito_user_pool_domain.learntrac.domain}.auth.${var.aws_region}.amazoncognito.com/login?client_id=${aws_cognito_user_pool_client.learntrac.id}&response_type=code&scope=email+openid+profile&redirect_uri=http://localhost:8000/auth/callback"
}