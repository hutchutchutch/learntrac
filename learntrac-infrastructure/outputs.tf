output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.learntrac.endpoint
}

output "rds_connection_string" {
  description = "PostgreSQL connection string for Trac"
  value       = "postgres://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.learntrac.endpoint}/${aws_db_instance.learntrac.db_name}"
  sensitive   = true
}

output "secret_manager_secret_name" {
  description = "AWS Secrets Manager secret name"
  value       = aws_secretsmanager_secret.db_password.name
}

output "security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

# Note: API Gateway outputs are defined in api-gateway-enhanced.tf

# ALB Outputs
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = try(module.alb.alb_dns_name, "ALB not deployed")
}

output "alb_url" {
  description = "URL to access the application"
  value       = try("http://${module.alb.alb_dns_name}", "ALB not deployed")
}

# ECR Repository URLs
output "trac_ecr_repository_url" {
  description = "URL of the Trac ECR repository"
  value       = try(aws_ecr_repository.trac.repository_url, "ECR not created")
}

output "learntrac_ecr_repository_url" {
  description = "URL of the LearnTrac ECR repository"
  value       = try(aws_ecr_repository.learntrac.repository_url, "ECR not created")
}

# ECS Cluster
output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = try(aws_ecs_cluster.main.name, "ECS cluster not created")
}

# Redis Endpoint
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = try(aws_elasticache_cluster.redis.cache_nodes[0].address, "Redis not created")
}

# Service URLs
output "service_urls" {
  description = "URLs for accessing different services"
  value = {
    trac_legacy    = try("http://${module.alb.alb_dns_name}/trac/", "Not deployed")
    learntrac_api  = try("http://${module.alb.alb_dns_name}/api/learntrac/health", "Not deployed")
    health_check   = try("http://${module.alb.alb_dns_name}/health", "Not deployed")
  }
}

# Secrets Manager ARNs
output "neo4j_secret_arn" {
  description = "ARN of the Neo4j credentials secret"
  value       = aws_secretsmanager_secret.neo4j_credentials.arn
}

output "openai_secret_arn" {
  description = "ARN of the OpenAI API key secret"
  value       = aws_secretsmanager_secret.openai_api_key.arn
}