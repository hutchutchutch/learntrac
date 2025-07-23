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

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.learntrac_users.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.learntrac_client.id
}

output "cognito_user_pool_endpoint" {
  value = aws_cognito_user_pool.learntrac_users.endpoint
}

output "cognito_domain" {
  value = aws_cognito_user_pool_domain.learntrac_domain.domain
}

output "cognito_domain_url" {
  value = "https://${aws_cognito_user_pool_domain.learntrac_domain.domain}.auth.${var.aws_region}.amazoncognito.com"
}