# ElastiCache Subnet Group for Redis
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.project_prefix}-redis-subnet"
  subnet_ids = data.aws_subnets.default.ids
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-redis-subnet-group"
  })
}

# Security Group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "${local.project_prefix}-redis-sg"
  vpc_id      = data.aws_vpc.default.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [
      module.trac_service.security_group_id,
      module.learntrac_service.security_group_id
    ]
    description = "Redis access from ECS services"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-redis-sg"
  })
}

# ElastiCache Redis Cluster
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.project_prefix}-redis"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  snapshot_retention_limit = var.environment == "prod" ? 5 : 0
  
  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-redis-cluster"
  })
}