# Security Updates for LearnTrac Infrastructure
# This file contains recommended security improvements

# Update RDS security group to allow ECS access
# resource "aws_security_group_rule" "rds_from_ecs_trac" {
#   type                     = "ingress"
#   from_port                = 5432
#   to_port                  = 5432
#   protocol                 = "tcp"
#   source_security_group_id = module.trac_service.security_group_id
#   security_group_id        = aws_security_group.rds.id
#   description              = "PostgreSQL access from Trac ECS service"
# }

resource "aws_security_group_rule" "rds_from_ecs_learntrac" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = module.learntrac_service.security_group_id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL access from LearnTrac API ECS service"
}

# VPC Flow Logs for security monitoring
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/${local.project_prefix}-flow-logs"
  retention_in_days = var.environment == "prod" ? 30 : 7
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-vpc-flow-logs"
  })
}

resource "aws_iam_role" "vpc_flow_logs" {
  name_prefix = "${local.project_prefix}-vpc-flow-logs-"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  name = "${local.project_prefix}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ]
      Resource = aws_cloudwatch_log_group.vpc_flow_logs.arn
    }]
  })
}

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0
  
  iam_role_arn    = aws_iam_role.vpc_flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = data.aws_vpc.default.id
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-vpc-flow-log"
  })
}

# AWS WAF WebACL for ALB protection (optional)
resource "aws_wafv2_web_acl" "main" {
  count = var.enable_waf ? 1 : 0
  
  name  = "${local.project_prefix}-waf"
  scope = "REGIONAL"
  
  default_action {
    allow {}
  }
  
  # Basic rate limiting rule
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
      metric_name                = "${local.project_prefix}-rate-limit"
      sampled_requests_enabled   = true
    }
  }
  
  # AWS Managed Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.project_prefix}-common-rules"
      sampled_requests_enabled   = true
    }
  }
  
  # SQL injection protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.project_prefix}-sqli-rules"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.project_prefix}-waf"
    sampled_requests_enabled   = true
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-waf"
  })
}

# Associate WAF with ALB
resource "aws_wafv2_web_acl_association" "main" {
  count = var.enable_waf ? 1 : 0
  
  resource_arn = module.alb.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main[0].arn
}

# GuardDuty for threat detection (optional)
resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0
  
  enable = true
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-guardduty"
  })
}

# Network ACL for additional subnet-level protection (optional)
# Commented out - need to fix data source reference
# resource "aws_network_acl_rule" "db_subnet_ingress_postgres" {
#   count = var.enable_network_acls ? 1 : 0
#   
#   network_acl_id = data.aws_network_acl.default.id
#   rule_number    = 100
#   protocol       = "tcp"
#   rule_action    = "allow"
#   cidr_block     = data.aws_vpc.default.cidr_block
#   from_port      = 5432
#   to_port        = 5432
# }

# resource "aws_network_acl_rule" "db_subnet_ingress_redis" {
#   count = var.enable_network_acls ? 1 : 0
#   
#   network_acl_id = data.aws_network_acl.default.id
#   rule_number    = 110
#   protocol       = "tcp"
#   rule_action    = "allow"
#   cidr_block     = data.aws_vpc.default.cidr_block
#   from_port      = 6379
#   to_port        = 6379
# }

# Data source for default Network ACL
data "aws_network_acls" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Hub for compliance monitoring (optional)
resource "aws_securityhub_account" "main" {
  count = var.enable_security_hub ? 1 : 0
}

# Enable AWS Config for compliance tracking (optional)
resource "aws_config_configuration_recorder" "main" {
  count = var.enable_aws_config ? 1 : 0
  
  name     = "${local.project_prefix}-config-recorder"
  role_arn = aws_iam_role.config[0].arn
  
  recording_group {
    all_supported = true
  }
}

resource "aws_iam_role" "config" {
  count = var.enable_aws_config ? 1 : 0
  
  name_prefix = "${local.project_prefix}-config-"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "config.amazonaws.com"
      }
    }]
  })
  
  tags = local.common_tags
}

# CloudWatch Alarms for security monitoring
resource "aws_cloudwatch_metric_alarm" "unauthorized_api_calls" {
  alarm_name          = "${local.project_prefix}-unauthorized-api-calls"
  alarm_description   = "Alert on unauthorized API calls"
  metric_name         = "UnauthorizedAPICalls"
  namespace           = "CloudTrailMetrics"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  
  tags = local.common_tags
}