# Fixed Security Group Rules

# Check if module outputs are different before creating rules
locals {
  # Get the actual security group IDs
  trac_sg_id      = module.trac_service.security_group_id
  learntrac_sg_id = module.learntrac_service.security_group_id
  
  # Check if they're the same (which is causing the duplicate)
  same_security_groups = local.trac_sg_id == local.learntrac_sg_id
}

# Only create the Trac rule if it's a different security group
resource "aws_security_group_rule" "rds_from_ecs_trac" {
  count = local.same_security_groups ? 0 : 1
  
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = local.trac_sg_id
  security_group_id        = aws_security_group.rds.id
  description              = "PostgreSQL access from Trac ECS service"
}

# Always create the LearnTrac rule (or rename if they're the same)
resource "aws_security_group_rule" "rds_from_ecs_services" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = local.learntrac_sg_id
  security_group_id        = aws_security_group.rds.id
  description              = local.same_security_groups ? "PostgreSQL access from ECS services" : "PostgreSQL access from LearnTrac API ECS service"
}