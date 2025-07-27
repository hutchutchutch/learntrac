# Monitoring and Observability Configuration

# CloudWatch Dashboard for API and Lambda monitoring
resource "aws_cloudwatch_dashboard" "learntrac_dashboard" {
  dashboard_name = "${local.project_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", { stat = "Sum", label = "API Calls" }],
            [".", "4XXError", { stat = "Sum", label = "4XX Errors" }],
            [".", "5XXError", { stat = "Sum", label = "5XX Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API Gateway Metrics"
          dimensions = {
            ApiName = aws_api_gateway_rest_api.learntrac.name
            Stage   = aws_api_gateway_stage.learntrac.stage_name
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { label = "Generate Invocations" }],
            [".", "Errors", { label = "Generate Errors" }],
            [".", "Duration", { stat = "Average", label = "Generate Duration" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "LLM Generate Lambda Metrics"
          dimensions = {
            FunctionName = aws_lambda_function.llm_generate.function_name
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { label = "Evaluate Invocations" }],
            [".", "Errors", { label = "Evaluate Errors" }],
            [".", "Duration", { stat = "Average", label = "Evaluate Duration" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "LLM Evaluate Lambda Metrics"
          dimensions = {
            FunctionName = aws_lambda_function.llm_evaluate.function_name
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", { stat = "Average", label = "Average Latency" }],
            [".", "Latency", { stat = "p99", label = "p99 Latency" }],
            [".", "Latency", { stat = "Maximum", label = "Max Latency" }]
          ]
          period = 300
          region = var.aws_region
          title  = "API Gateway Latency"
          dimensions = {
            ApiName = aws_api_gateway_rest_api.learntrac.name
            Stage   = aws_api_gateway_stage.learntrac.stage_name
          }
        }
      }
    ]
  })
}

# X-Ray tracing for Lambda functions (already configured in lambda-llm.tf)

# CloudWatch Logs Insights queries
resource "aws_cloudwatch_query_definition" "lambda_errors" {
  name = "${local.project_prefix}-lambda-errors"

  log_group_names = [
    aws_cloudwatch_log_group.llm_generate.name,
    aws_cloudwatch_log_group.llm_evaluate.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /ERROR/
    | sort @timestamp desc
    | limit 50
  EOT
}

resource "aws_cloudwatch_query_definition" "api_gateway_errors" {
  name = "${local.project_prefix}-api-gateway-errors"

  log_group_names = [
    aws_cloudwatch_log_group.api_gateway.name
  ]

  query_string = <<-EOT
    fields @timestamp, status, error, integrationError, sourceIp, userAgent
    | filter status >= 400
    | sort @timestamp desc
    | limit 50
  EOT
}

resource "aws_cloudwatch_query_definition" "llm_usage_stats" {
  name = "${local.project_prefix}-llm-usage-stats"

  log_group_names = [
    aws_cloudwatch_log_group.llm_generate.name,
    aws_cloudwatch_log_group.llm_evaluate.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message
    | parse @message /Generated (?<count>\d+) questions for difficulty (?<difficulty>\d+)/
    | parse @message /Evaluated answer with score: (?<score>\d+\.\d+)/
    | stats count() by bin(5m)
  EOT
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.project_prefix}-alerts"

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-alerts-topic"
  })
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda error alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors_generate" {
  alarm_name          = "${local.project_prefix}-lambda-generate-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "Errors"
  namespace          = "AWS/Lambda"
  period             = "300"
  statistic          = "Sum"
  threshold          = "5"
  alarm_description  = "LLM Generate Lambda errors"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.llm_generate.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-lambda-generate-errors-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors_evaluate" {
  alarm_name          = "${local.project_prefix}-lambda-evaluate-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "Errors"
  namespace          = "AWS/Lambda"
  period             = "300"
  statistic          = "Sum"
  threshold          = "5"
  alarm_description  = "LLM Evaluate Lambda errors"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.llm_evaluate.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-lambda-evaluate-errors-alarm"
  })
}

# Lambda throttling alarms
resource "aws_cloudwatch_metric_alarm" "lambda_throttles_generate" {
  alarm_name          = "${local.project_prefix}-lambda-generate-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name        = "Throttles"
  namespace          = "AWS/Lambda"
  period             = "300"
  statistic          = "Sum"
  threshold          = "10"
  alarm_description  = "LLM Generate Lambda throttles"
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.llm_generate.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-lambda-generate-throttles-alarm"
  })
}

# Variable for alert email
variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
  default     = ""
}

# Outputs
output "dashboard_url" {
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.learntrac_dashboard.dashboard_name}"
  description = "URL to CloudWatch dashboard"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic ARN for alerts"
}