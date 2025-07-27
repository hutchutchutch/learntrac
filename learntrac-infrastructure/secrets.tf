# Neo4j Credentials Secret
resource "aws_secretsmanager_secret" "neo4j_credentials" {
  name        = "${local.project_prefix}-neo4j-credentials"
  description = "Neo4j credentials for ${var.owner_prefix} ${var.project_name} - ${var.environment}"
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-neo4j-secret"
  })
}

resource "aws_secretsmanager_secret_version" "neo4j_credentials" {
  secret_id = aws_secretsmanager_secret.neo4j_credentials.id
  secret_string = jsonencode({
    uri      = var.neo4j_uri != "" ? var.neo4j_uri : "neo4j+s://your-instance.databases.neo4j.io"
    username = "neo4j"
    password = var.neo4j_password != "" ? var.neo4j_password : "nrZPSVB9oOCjSQ442WCRIpUdvDbO_XHOdaIZof7KjNE"
  })
}

# Note: OpenAI API Key Secret is defined in lambda-llm.tf
# Commenting out duplicate resource
# resource "aws_secretsmanager_secret" "openai_api_key" {
#   name        = "${local.project_prefix}-openai-api-key"
#   description = "OpenAI API key for ${var.owner_prefix} ${var.project_name} - ${var.environment}"
#   
#   tags = merge(local.common_tags, {
#     Name = "${local.project_prefix}-openai-secret"
#   })
# }
# 
# resource "aws_secretsmanager_secret_version" "openai_api_key" {
#   secret_id = aws_secretsmanager_secret.openai_api_key.id
#   secret_string = jsonencode({
#     api_key = var.openai_api_key
#   })
# }