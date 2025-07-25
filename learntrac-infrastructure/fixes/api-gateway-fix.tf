# Fixed API Gateway Configuration

# API Gateway deployment without deprecated stage_name
resource "aws_api_gateway_deployment" "learntrac_api" {
  rest_api_id = aws_api_gateway_rest_api.learntrac_api.id
  
  # Remove the deprecated stage_name parameter
  # stage_name is now managed by aws_api_gateway_stage resource
  
  triggers = {
    redeployment = sha256(jsonencode([
      aws_api_gateway_rest_api.learntrac_api.id,
      aws_api_gateway_authorizer.cognito.id,
      aws_api_gateway_resource.auth.id,
      aws_api_gateway_resource.api.id,
      aws_api_gateway_resource.v1.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Import existing stage or handle it properly
resource "aws_api_gateway_stage" "learntrac_stage" {
  deployment_id = aws_api_gateway_deployment.learntrac_api.id
  rest_api_id   = aws_api_gateway_rest_api.learntrac_api.id
  stage_name    = var.environment

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format         = jsonencode({
      requestId        = "$context.requestId"
      requestTime      = "$context.requestTime"
      requestTimeEpoch = "$context.requestTimeEpoch"
      httpMethod       = "$context.httpMethod"
      resourcePath     = "$context.resourcePath"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      error            = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
      authorizerError  = "$context.authorizer.error"
      authLatency      = "$context.authorizer.latency"
      integrationLatency = "$context.integration.latency"
      responseLatency    = "$context.responseLatency"
    })
  }

  xray_tracing_enabled = true

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-stage"
  })
}