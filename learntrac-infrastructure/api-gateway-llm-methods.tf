# API Gateway Methods and Integrations for LLM endpoints

# POST /api/v1/llm/generate
resource "aws_api_gateway_method" "llm_generate" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.llm_generate.id
  http_method   = "POST"
  authorization = "NONE"  # Changed from COGNITO_USER_POOLS
  # authorizer_id = aws_api_gateway_authorizer.cognito.id  # Cognito removed

  # authorization_scopes = [
  #   "${aws_cognito_resource_server.learntrac_api.identifier}/write"
  # ]  # Cognito removed

  request_validator_id = aws_api_gateway_request_validator.learntrac_validator.id

  request_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_generate.id
  http_method = aws_api_gateway_method.llm_generate.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.llm_generate.invoke_arn
}

resource "aws_api_gateway_method_response" "llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_generate.id
  http_method = aws_api_gateway_method.llm_generate.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# POST /api/v1/llm/evaluate
resource "aws_api_gateway_method" "llm_evaluate" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.llm_evaluate.id
  http_method   = "POST"
  authorization = "NONE"  # Changed from COGNITO_USER_POOLS
  # authorizer_id = aws_api_gateway_authorizer.cognito.id  # Cognito removed

  # authorization_scopes = [
  #   "${aws_cognito_resource_server.learntrac_api.identifier}/write"
  # ]  # Cognito removed

  request_validator_id = aws_api_gateway_request_validator.learntrac_validator.id

  request_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration" "llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_evaluate.id
  http_method = aws_api_gateway_method.llm_evaluate.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.llm_evaluate.invoke_arn
}

resource "aws_api_gateway_method_response" "llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_evaluate.id
  http_method = aws_api_gateway_method.llm_evaluate.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# OPTIONS methods for CORS
resource "aws_api_gateway_method" "options_llm_generate" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.llm_generate.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_generate.id
  http_method = aws_api_gateway_method.options_llm_generate.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "options_llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_generate.id
  http_method = aws_api_gateway_method.options_llm_generate.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_llm_generate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_generate.id
  http_method = aws_api_gateway_method.options_llm_generate.http_method
  status_code = aws_api_gateway_method_response.options_llm_generate.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_method" "options_llm_evaluate" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.llm_evaluate.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_evaluate.id
  http_method = aws_api_gateway_method.options_llm_evaluate.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "options_llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_evaluate.id
  http_method = aws_api_gateway_method.options_llm_evaluate.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_llm_evaluate" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.llm_evaluate.id
  http_method = aws_api_gateway_method.options_llm_evaluate.http_method
  status_code = aws_api_gateway_method_response.options_llm_evaluate.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Learning paths endpoints
# POST /api/v1/learning-paths
resource "aws_api_gateway_method" "create_learning_path" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.learning_paths.id
  http_method   = "POST"
  authorization = "NONE"  # Changed from COGNITO_USER_POOLS
  # authorizer_id = aws_api_gateway_authorizer.cognito.id  # Cognito removed

  # authorization_scopes = [
  #   "${aws_cognito_resource_server.learntrac_api.identifier}/write"
  # ]  # Cognito removed

  request_validator_id = aws_api_gateway_request_validator.learntrac_validator.id
}

# For now, using MOCK integration - replace with actual backend integration
resource "aws_api_gateway_integration" "create_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths.id
  http_method = aws_api_gateway_method.create_learning_path.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "create_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths.id
  http_method = aws_api_gateway_method.create_learning_path.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "create_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths.id
  http_method = aws_api_gateway_method.create_learning_path.http_method
  status_code = aws_api_gateway_method_response.create_learning_path.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = jsonencode({
      pathId = "mock-path-id"
      message = "Learning path created successfully"
    })
  }
}

# GET /api/v1/learning-paths/{pathId}
resource "aws_api_gateway_method" "get_learning_path" {
  rest_api_id   = aws_api_gateway_rest_api.learntrac.id
  resource_id   = aws_api_gateway_resource.learning_paths_id.id
  http_method   = "GET"
  authorization = "NONE"  # Changed from COGNITO_USER_POOLS
  # authorizer_id = aws_api_gateway_authorizer.cognito.id  # Cognito removed

  # authorization_scopes = [
  #   "${aws_cognito_resource_server.learntrac_api.identifier}/read"
  # ]  # Cognito removed

  request_parameters = {
    "method.request.path.pathId" = true
  }
}

# MOCK integration for GET learning path
resource "aws_api_gateway_integration" "get_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths_id.id
  http_method = aws_api_gateway_method.get_learning_path.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "get_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths_id.id
  http_method = aws_api_gateway_method.get_learning_path.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_integration_response" "get_learning_path" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  resource_id = aws_api_gateway_resource.learning_paths_id.id
  http_method = aws_api_gateway_method.get_learning_path.http_method
  status_code = aws_api_gateway_method_response.get_learning_path.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  response_templates = {
    "application/json" = jsonencode({
      pathId = "$input.params('pathId')"
      title = "Mock Learning Path"
      tickets = []
    })
  }
}