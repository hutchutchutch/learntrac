# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnet_ids
  
  enable_deletion_protection = var.environment == "prod"
  enable_http2              = true
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb"
  })
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name_prefix = "${var.name_prefix}-alb-sg"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from anywhere"
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-sg"
  })
}

# Target Group for Trac (Python 2.7)
resource "aws_lb_target_group" "trac" {
  name_prefix = "trac-"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/trac/login"
    port                = "traffic-port"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-trac-tg"
  })
}

# Target Group for LearnTrac API (Python 3.11)
resource "aws_lb_target_group" "learntrac" {
  name_prefix = "learn-"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api/learntrac/health"
    port                = "traffic-port"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-learntrac-tg"
  })
}

# HTTPS Listener (only if certificate provided)
resource "aws_lb_listener" "https" {
  count = var.certificate_arn != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

# HTTP Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = var.certificate_arn != "" ? "redirect" : "fixed-response"
    
    dynamic "redirect" {
      for_each = var.certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
    
    dynamic "fixed_response" {
      for_each = var.certificate_arn == "" ? [1] : []
      content {
        content_type = "text/plain"
        message_body = "Welcome to TracLearn"
        status_code  = "200"
      }
    }
  }
}

# Path-based routing for Trac - Split into multiple rules due to AWS 5-path limit
resource "aws_lb_listener_rule" "trac_paths_1" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 100
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "/trac/*",
        "/ticket/*",
        "/wiki/*",
        "/timeline/*",
        "/roadmap/*"
      ]
    }
  }
}

resource "aws_lb_listener_rule" "trac_paths_2" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 101
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "/browser/*",
        "/changeset/*",
        "/attachment/*",
        "/login",
        "/logout"
      ]
    }
  }
}

# Path-based routing for LearnTrac API
resource "aws_lb_listener_rule" "learntrac_api" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 90
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.learntrac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "/api/learntrac/*",
        "/api/chat/*",
        "/api/voice/*",
        "/api/analytics/*"
      ]
    }
  }
}

# Static assets routing - Split into multiple rules due to AWS 5-path limit
resource "aws_lb_listener_rule" "static_assets_1" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 80
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "/chrome/*",
        "/static/*",
        "*.css",
        "*.js",
        "*.png"
      ]
    }
  }
}

resource "aws_lb_listener_rule" "static_assets_2" {
  listener_arn = var.certificate_arn != "" ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
  priority     = 81
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "*.jpg",
        "*.ico"
      ]
    }
  }
}