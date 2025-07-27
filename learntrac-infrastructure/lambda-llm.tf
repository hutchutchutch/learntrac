# Lambda Functions for LLM Integration

# IAM role for LLM Lambda functions
resource "aws_iam_role" "llm_lambda" {
  name = "${local.project_prefix}-llm-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "llm_lambda_basic" {
  role       = aws_iam_role.llm_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for accessing Secrets Manager (for API keys)
resource "aws_iam_policy" "llm_lambda_secrets" {
  name        = "${local.project_prefix}-llm-lambda-secrets"
  description = "Allow Lambda to access OpenAI API key from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.openai_api_key.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "llm_lambda_secrets" {
  role       = aws_iam_role.llm_lambda.name
  policy_arn = aws_iam_policy.llm_lambda_secrets.arn
}

# Policy for CloudWatch Logs
resource "aws_iam_policy" "llm_lambda_logs" {
  name        = "${local.project_prefix}-llm-lambda-logs"
  description = "Allow Lambda to write to CloudWatch Logs"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "llm_lambda_logs" {
  role       = aws_iam_role.llm_lambda.name
  policy_arn = aws_iam_policy.llm_lambda_logs.arn
}

# Store OpenAI API Key in Secrets Manager
resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "${local.project_prefix}-openai-api-key"
  description = "OpenAI API key for LLM integration"
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-openai-secret"
  })
}

# Note: The actual API key value should be set manually or via CI/CD
# terraform apply -var="openai_api_key=sk-..."
resource "aws_secretsmanager_secret_version" "openai_api_key" {
  count         = var.openai_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.openai_api_key
}

# Lambda Layer for OpenAI SDK and dependencies
# Note: Lambda layer commented out - ZIP file needs to be created
# resource "aws_lambda_layer_version" "openai_sdk" {
#   filename            = "lambda/layers/openai-sdk-layer.zip"
#   layer_name          = "${local.project_prefix}-openai-sdk"
#   compatible_runtimes = ["python3.11", "python3.10"]
#   description         = "OpenAI SDK and dependencies"
# 
#   source_code_hash = filebase64sha256("lambda/layers/openai-sdk-layer.zip")
# }

# Lambda function for question generation
resource "aws_lambda_function" "llm_generate" {
  filename         = "lambda/llm-generate.zip"
  function_name    = "${local.project_prefix}-llm-generate"
  role            = aws_iam_role.llm_lambda.arn
  handler         = "llm_generate.handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512
  source_code_hash = filebase64sha256("lambda/llm-generate.zip")

  # layers = [aws_lambda_layer_version.openai_sdk.arn]  # Commented out - layer needs to be created

  environment {
    variables = {
      OPENAI_API_KEY_SECRET = aws_secretsmanager_secret.openai_api_key.name
      ENVIRONMENT           = var.environment
      MODEL_NAME            = var.llm_model_name
      MAX_TOKENS           = var.llm_max_tokens
      TEMPERATURE          = var.llm_temperature
    }
  }

  tracing_config {
    mode = var.environment == "prod" ? "Active" : "PassThrough"
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-llm-generate-lambda"
  })
}

# Lambda function for answer evaluation
resource "aws_lambda_function" "llm_evaluate" {
  filename         = "lambda/llm-evaluate.zip"
  function_name    = "${local.project_prefix}-llm-evaluate"
  role            = aws_iam_role.llm_lambda.arn
  handler         = "llm_evaluate.handler"
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 512
  source_code_hash = filebase64sha256("lambda/llm-evaluate.zip")

  # layers = [aws_lambda_layer_version.openai_sdk.arn]  # Commented out - layer needs to be created

  environment {
    variables = {
      OPENAI_API_KEY_SECRET = aws_secretsmanager_secret.openai_api_key.name
      ENVIRONMENT           = var.environment
      MODEL_NAME            = var.llm_model_name
      MAX_TOKENS           = var.llm_max_tokens
      TEMPERATURE          = var.llm_temperature
    }
  }

  tracing_config {
    mode = var.environment == "prod" ? "Active" : "PassThrough"
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-llm-evaluate-lambda"
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "llm_generate" {
  name              = "/aws/lambda/${aws_lambda_function.llm_generate.function_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-llm-generate-logs"
  })
}

resource "aws_cloudwatch_log_group" "llm_evaluate" {
  name              = "/aws/lambda/${aws_lambda_function.llm_evaluate.function_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-llm-evaluate-logs"
  })
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "llm_generate_apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.llm_generate.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.learntrac.execution_arn}/*/*"
}

resource "aws_lambda_permission" "llm_evaluate_apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.llm_evaluate.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.learntrac.execution_arn}/*/*"
}

# Outputs
output "llm_generate_function_arn" {
  value       = aws_lambda_function.llm_generate.arn
  description = "ARN of the LLM generate Lambda function"
}

output "llm_evaluate_function_arn" {
  value       = aws_lambda_function.llm_evaluate.arn
  description = "ARN of the LLM evaluate Lambda function"
}

output "openai_api_key_secret_arn" {
  value       = aws_secretsmanager_secret.openai_api_key.arn
  description = "ARN of the OpenAI API key secret"
}