# Rate Limiting and Throttling Configuration for API Gateway

# API Keys for rate limiting
resource "aws_api_gateway_api_key" "learntrac_default" {
  name        = "${local.project_prefix}-default-api-key"
  description = "Default API key for LearnTrac"
  enabled     = true

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-default-api-key"
  })
}

# Usage plan for LLM endpoints with stricter limits
resource "aws_api_gateway_usage_plan" "llm_plan" {
  name        = "${local.project_prefix}-llm-usage-plan"
  description = "Usage plan for LLM endpoints with rate limiting"

  api_stages {
    api_id = aws_api_gateway_rest_api.learntrac.id
    stage  = aws_api_gateway_stage.learntrac.stage_name
  }

  quota_settings {
    limit  = var.environment == "prod" ? 1000 : 100  # Daily quota
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = var.environment == "prod" ? 10 : 5   # Requests per second
    burst_limit = var.environment == "prod" ? 20 : 10  # Burst capacity
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-llm-usage-plan"
  })
}

# Associate API key with usage plan
resource "aws_api_gateway_usage_plan_key" "llm_plan_key" {
  key_id        = aws_api_gateway_api_key.learntrac_default.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.llm_plan.id
}

# General method settings for all API Gateway methods
resource "aws_api_gateway_method_settings" "general_settings" {
  rest_api_id = aws_api_gateway_rest_api.learntrac.id
  stage_name  = aws_api_gateway_stage.learntrac.stage_name
  method_path = "*/*"  # Apply to all methods in stage

  settings {
    metrics_enabled        = true
    logging_level         = var.environment == "prod" ? "ERROR" : "INFO"
    data_trace_enabled    = var.environment != "prod"
    throttling_rate_limit = var.environment == "prod" ? 10 : 5
    throttling_burst_limit = var.environment == "prod" ? 20 : 10
  }

  depends_on = [aws_api_gateway_deployment.learntrac]
}

# WAF Web ACL for additional protection (optional, for production)
resource "aws_wafv2_web_acl" "api_protection" {
  count = var.environment == "prod" ? 1 : 0
  
  name  = "${local.project_prefix}-api-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimitRule"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "${local.project_prefix}-rate-limit"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "${local.project_prefix}-waf"
    sampled_requests_enabled  = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-api-waf"
  })
}

# Associate WAF with API Gateway
resource "aws_wafv2_web_acl_association" "api_gateway" {
  count = var.environment == "prod" ? 1 : 0
  
  resource_arn = aws_api_gateway_stage.learntrac.arn
  web_acl_arn  = aws_wafv2_web_acl.api_protection[0].arn
}

# CloudWatch alarms for monitoring API usage
resource "aws_cloudwatch_metric_alarm" "high_4xx_errors" {
  alarm_name          = "${local.project_prefix}-high-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "4XXError"
  namespace          = "AWS/ApiGateway"
  period             = "300"
  statistic          = "Sum"
  threshold          = var.environment == "prod" ? "50" : "10"
  alarm_description  = "This metric monitors 4xx errors"
  treat_missing_data = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.learntrac.name
    Stage   = aws_api_gateway_stage.learntrac.stage_name
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-4xx-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "${local.project_prefix}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "Latency"
  namespace          = "AWS/ApiGateway"
  period             = "300"
  statistic          = "Average"
  threshold          = "1000"  # 1 second
  alarm_description  = "This metric monitors API latency"
  treat_missing_data = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.learntrac.name
    Stage   = aws_api_gateway_stage.learntrac.stage_name
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-latency-alarm"
  })
}

# Output rate limiting information
output "api_key_id" {
  value       = aws_api_gateway_api_key.learntrac_default.id
  description = "Default API key ID"
  sensitive   = true
}

output "api_key_value" {
  value       = aws_api_gateway_api_key.learntrac_default.value
  description = "Default API key value"
  sensitive   = true
}