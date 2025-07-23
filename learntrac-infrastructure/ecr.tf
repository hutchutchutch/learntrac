# ECR Repository for Trac (Python 2.7)
resource "aws_ecr_repository" "trac" {
  name                 = "${local.project_prefix}-trac"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-trac-ecr"
  })
}

# ECR Lifecycle Policy for Trac
resource "aws_ecr_lifecycle_policy" "trac" {
  repository = aws_ecr_repository.trac.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ECR Repository for LearnTrac API (Python 3.11)
resource "aws_ecr_repository" "learntrac" {
  name                 = "${local.project_prefix}-learntrac"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-learntrac-ecr"
  })
}

# ECR Lifecycle Policy for LearnTrac
resource "aws_ecr_lifecycle_policy" "learntrac" {
  repository = aws_ecr_repository.learntrac.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}