# ECS Cluster for both Trac and LearnTrac services
resource "aws_ecs_cluster" "main" {
  name = "${local.project_prefix}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-ecs-cluster"
  })
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  name_prefix     = local.project_prefix
  vpc_id          = data.aws_vpc.default.id
  subnet_ids      = data.aws_subnets.default.ids
  certificate_arn = var.ssl_certificate_arn
  environment     = var.environment
  tags            = local.common_tags
}

# Trac Service (Python 2.7)
module "trac_service" {
  source = "./modules/ecs"
  
  name_prefix      = "${local.project_prefix}-trac"
  cluster_id       = aws_ecs_cluster.main.id
  cluster_name     = aws_ecs_cluster.main.name
  vpc_id           = data.aws_vpc.default.id
  subnet_ids       = data.aws_subnets.default.ids
  
  container_image  = "${aws_ecr_repository.trac.repository_url}:latest"
  container_port   = 8000
  cpu              = var.trac_cpu
  memory           = var.trac_memory
  desired_count    = var.trac_desired_count
  min_count        = var.trac_min_count
  max_count        = var.trac_max_count
  
  environment_variables = {
    TRAC_ENV         = "/var/trac/projects"
    DATABASE_URL     = "postgres://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.learntrac.endpoint}/${var.project_name}"
    PYTHON_VERSION   = "2.7"
  }
  
  target_group_arn       = module.alb.trac_target_group_arn
  alb_security_group_ids = [module.alb.alb_security_group_id]
  
  tags = local.common_tags
}

# LearnTrac API Service (Python 3.11)
module "learntrac_service" {
  source = "./modules/ecs"
  
  name_prefix      = "${local.project_prefix}-learntrac"
  cluster_id       = aws_ecs_cluster.main.id
  cluster_name     = aws_ecs_cluster.main.name
  vpc_id           = data.aws_vpc.default.id
  subnet_ids       = data.aws_subnets.default.ids
  
  container_image  = "${aws_ecr_repository.learntrac.repository_url}:latest"
  container_port   = 8001
  cpu              = var.learntrac_cpu
  memory           = var.learntrac_memory
  desired_count    = var.learntrac_desired_count
  min_count        = var.learntrac_min_count
  max_count        = var.learntrac_max_count
  
  environment_variables = {
    DATABASE_URL     = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.learntrac.endpoint}/${var.project_name}"
    REDIS_URL        = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    PYTHON_VERSION   = "3.11"
    COGNITO_POOL_ID  = aws_cognito_user_pool.learntrac_users.id
    COGNITO_CLIENT_ID = aws_cognito_user_pool_client.learntrac_client.id
    AWS_REGION       = var.aws_region
  }
  
  secret_variables = {
    NEO4J_URI      = "${aws_secretsmanager_secret.neo4j_credentials.arn}:uri::"
    NEO4J_USER     = "${aws_secretsmanager_secret.neo4j_credentials.arn}:username::"
    NEO4J_PASSWORD = "${aws_secretsmanager_secret.neo4j_credentials.arn}:password::"
    OPENAI_API_KEY = "${aws_secretsmanager_secret.openai_api_key.arn}:api_key::"
  }
  
  target_group_arn       = module.alb.learntrac_target_group_arn
  alb_security_group_ids = [module.alb.alb_security_group_id]
  
  tags = local.common_tags
}