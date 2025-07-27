# Enhanced API Gateway Configuration with Cognito Authorization

# Create request validator
resource "aws_api_gateway_request_validator" "learntrac_validator" {
  name                        = "${local.project_prefix}-request-validator"
  rest_api_id                 = aws_api_gateway_rest_api.learntrac.id
  validate_request_body       = true
  validate_request_parameters = true
}

# API Gateway deployment (moved from main.tf to ensure methods exist)
resource "aws_api_gateway_deployment" "learntrac" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  
  # Force new deployment when configuration changes
  triggers = {
    redeployment = sha256(jsonencode([
      aws_api_gateway_rest_api.learntrac.id,
      aws_api_gateway_resource.auth_new.id,
      aws_api_gateway_resource.api_new.id,
      aws_api_gateway_resource.v1_new.id,
      aws_api_gateway_resource.learning_paths.id,
      aws_api_gateway_resource.llm.id,
      aws_api_gateway_method.options_auth.id,
      aws_api_gateway_method.options_api.id,
      aws_api_gateway_method.get_courses.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
  
  # Ensure methods are created before deployment
  depends_on = [
    aws_api_gateway_method.options_auth,
    aws_api_gateway_method.options_api, 
    aws_api_gateway_method.get_courses,
    aws_api_gateway_integration.options_auth,
    aws_api_gateway_integration.options_api,
    aws_api_gateway_integration.get_courses,
    aws_api_gateway_method_response.options_auth,
    aws_api_gateway_method_response.options_api,
    aws_api_gateway_method_response.get_courses,
    aws_api_gateway_integration_response.options_auth,
    aws_api_gateway_integration_response.options_api,
    aws_api_gateway_integration_response.get_courses,
  ]
}

# NOTE: API Gateway stage is defined in main.tf
# Commenting out duplicate resource
# resource "aws_api_gateway_stage" "learntrac_stage" {
#   deployment_id = aws_api_gateway_deployment.learntrac.id
#   rest_api_id   = aws_api_gateway_rest_api.learntrac.id
#   stage_name    = var.environment
# 
#   access_log_settings {
#     destination_arn = aws_cloudwatch_log_group.api_gateway.arn
#     format         = jsonencode({
#       requestId        = "$context.requestId"
#       requestTime      = "$context.requestTime"
#       requestTimeEpoch = "$context.requestTimeEpoch"
#       httpMethod       = "$context.httpMethod"
#       resourcePath     = "$context.resourcePath"
#       status           = "$context.status"
#       protocol         = "$context.protocol"
#       responseLength   = "$context.responseLength"
#       error            = "$context.error.message"
#       integrationError = "$context.integrationErrorMessage"
#       sourceIp         = "$context.identity.sourceIp"
#       userAgent        = "$context.identity.userAgent"
#       # cognitoUser      = "$context.authorizer.claims.sub"  # Cognito removed
#     })
#   }
# 
#   xray_tracing_enabled = var.environment == "prod"
# 
#   tags = merge(local.common_tags, {
#     Name = "${local.project_prefix}-api-stage-${var.environment}"
#   })
# }

# NOTE: CloudWatch Log Group is defined in main.tf
# Commenting out duplicate resource
# resource "aws_cloudwatch_log_group" "api_gateway_logs" {
#   name              = "/aws/apigateway/${local.project_prefix}"
#   retention_in_days = var.environment == "prod" ? 30 : 7
# 
#   tags = merge(local.common_tags, {
#     Name = "${local.project_prefix}-api-logs"
#   })
# }

# API Gateway resources structure
# /auth resources (public endpoints)
resource "aws_api_gateway_resource" "auth_new" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_rest_api.learntrac.root_resource_id
  path_part   = "auth"
}

resource "aws_api_gateway_resource" "auth_login" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.auth_new.id
  path_part   = "login"
}

resource "aws_api_gateway_resource" "auth_refresh" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.auth_new.id
  path_part   = "refresh"
}

resource "aws_api_gateway_resource" "auth_logout" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.auth_new.id
  path_part   = "logout"
}

# /api resources (protected endpoints)
resource "aws_api_gateway_resource" "api_new" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_rest_api.learntrac.root_resource_id
  path_part   = "api"
}

resource "aws_api_gateway_resource" "v1_new" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.api_new.id
  path_part   = "v1"
}

# Learning endpoints
resource "aws_api_gateway_resource" "learning" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.v1_new.id
  path_part   = "learning"
}

resource "aws_api_gateway_resource" "courses" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.learning.id
  path_part   = "courses"
}

resource "aws_api_gateway_resource" "courses_id" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.courses.id
  path_part   = "{courseId}"
}

resource "aws_api_gateway_resource" "assignments" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.learning.id
  path_part   = "assignments"
}

# Trac endpoints
resource "aws_api_gateway_resource" "trac" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.v1_new.id
  path_part   = "trac"
}

resource "aws_api_gateway_resource" "tickets" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.trac.id
  path_part   = "tickets"
}

resource "aws_api_gateway_resource" "wiki" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.trac.id
  path_part   = "wiki"
}

# Learning paths endpoints
resource "aws_api_gateway_resource" "learning_paths" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.v1_new.id
  path_part   = "learning-paths"
}

resource "aws_api_gateway_resource" "learning_paths_id" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.learning_paths.id
  path_part   = "{pathId}"
}

# LLM endpoints
resource "aws_api_gateway_resource" "llm" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.v1_new.id
  path_part   = "llm"
}

resource "aws_api_gateway_resource" "llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.llm.id
  path_part   = "generate"
}

resource "aws_api_gateway_resource" "llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  parent_id   = aws_api_gateway_resource.llm.id
  path_part   = "evaluate"
}

# CORS configuration for all endpoints
resource "aws_api_gateway_method" "options_auth" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.auth_new.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "options_api" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.api_new.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS integration
resource "aws_api_gateway_integration" "options_auth" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.auth_new.id
  http_method = aws_api_gateway_method.options_auth.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_integration" "options_api" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.api_new.id
  http_method = aws_api_gateway_method.options_api.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

# CORS method responses
resource "aws_api_gateway_method_response" "options_auth" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.auth_new.id
  http_method = aws_api_gateway_method.options_auth.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_method_response" "options_api" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.api_new.id
  http_method = aws_api_gateway_method.options_api.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# CORS integration responses
resource "aws_api_gateway_integration_response" "options_auth" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.auth_new.id
  http_method = aws_api_gateway_method.options_auth.http_method
  status_code = aws_api_gateway_method_response.options_auth.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_integration_response" "options_api" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.api_new.id
  http_method = aws_api_gateway_method.options_api.http_method
  status_code = aws_api_gateway_method_response.options_api.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Example protected endpoint - GET /api/v1/learning/courses
resource "aws_api_gateway_method" "get_courses" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.courses.id
  http_method   = "GET"
  authorization = "NONE"  # Changed from COGNITO_USER_POOLS
  # authorizer_id = aws_api_gateway_authorizer.cognito.id  # Cognito removed

  # authorization_scopes = [
  #   "${aws_cognito_resource_server.learntrac_api.identifier}/read"
  # ]  # Cognito removed
}

# Lambda integration example (placeholder - replace with actual Lambda ARN)
resource "aws_api_gateway_integration" "get_courses" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.courses.id
  http_method = aws_api_gateway_method.get_courses.http_method
  
  # For now, using MOCK integration - replace with Lambda or HTTP integration
  type = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Method response for GET courses
resource "aws_api_gateway_method_response" "get_courses" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.courses.id
  http_method = aws_api_gateway_method.get_courses.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration response for GET courses
resource "aws_api_gateway_integration_response" "get_courses" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.courses.id
  http_method = aws_api_gateway_method.get_courses.http_method
  status_code = aws_api_gateway_method_response.get_courses.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = jsonencode({
      courses = [
        {
          id = "course-1"
          title = "Introduction to Trac"
          description = "Learn the basics of Trac project management"
        }
      ]
    })
  }
}

# API Gateway usage plan
resource "aws_api_gateway_usage_plan" "learntrac_plan" {
  name        = "${local.project_prefix}-usage-plan"
  description = "Usage plan for LearnTrac API"

  api_stages {
    api_id = aws_api_gateway_rest_api.learntrac.id
    stage  = aws_api_gateway_stage.learntrac.stage_name
  }

  quota_settings {
    limit  = 10000
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = 100
    burst_limit = 200
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-usage-plan"
  })
  
  # Add explicit dependencies to avoid cycles
  depends_on = [
    aws_api_gateway_deployment.learntrac,
    aws_api_gateway_stage.learntrac
  ]
}

# Output API Gateway details
output "api_gateway_url" {
  value       = "https://${aws_api_gateway_rest_api.learntrac.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.learntrac.stage_name}"
  description = "API Gateway invoke URL"
}

output "api_gateway_id" {
  value       = aws_api_gateway_rest_api.learntrac.id
  description = "API Gateway REST API ID"
}

output "api_gateway_stage_name" {
  value       = aws_api_gateway_stage.learntrac.stage_name
  description = "API Gateway stage name"
}

# output "api_gateway_authorizer_id" {
#   value       = aws_api_gateway_authorizer.cognito.id
#   description = "Cognito authorizer ID for API Gateway"
# }  # Cognito removed# Fix for API Gateway CloudWatch Logs

# Create IAM role for API Gateway CloudWatch Logs
resource "aws_iam_role" "api_gateway_cloudwatch" {
  name = "${local.project_prefix}-api-gateway-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  role       = aws_iam_role.api_gateway_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Set API Gateway account settings
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch.arn
}