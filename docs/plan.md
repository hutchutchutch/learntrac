Looking at your situation with a Python 2.7 Trac project that you want to extend with modern Python 3+ features, you have several architectural options on AWS without migrating the entire codebase. Here's a comprehensive strategy:
1. Microservices Architecture with API Gateway
The cleanest approach is to keep Trac running on Python 2.7 while building new LearnTrac features as separate Python 3+ microservices:
┌─────────────────────────────────────────────────────────────┐
│                   AWS Architecture                          │
├─────────────────────────────────────────────────────────────┤
│  API Gateway / Application Load Balancer                    │
│     ├── /trac/* → EC2/ECS (Python 2.7 Trac)               │
│     ├── /api/LearnTrac/* → Lambda/ECS (Python 3.11+)       │
│     ├── /voice/* → Lambda (Python 3.11 + FastRTC)          │
│     └── /chat/* → Lambda (Python 3.11 + AI Services)       │
└─────────────────────────────────────────────────────────────┘
2. Implementation Options
Option A: Lambda Functions for New Features (Recommended)
python# lambda_functions/LearnTrac_api/handler.py (Python 3.11)
import json
import boto3
from neo4j import GraphDatabase

def get_learning_progress(event, context):
    """Lambda function for LearnTrac progress API"""
    student_id = event['pathParameters']['student_id']
    
    # Connect to Neo4j (hosted separately)
    neo4j_driver = GraphDatabase.driver(
        os.environ['NEO4J_URI'],
        auth=(os.environ['NEO4J_USER'], os.environ['NEO4J_PASSWORD'])
    )
    
    # Modern Python 3.11 features available here
    match event['httpMethod']:
        case 'GET':
            return get_student_progress(student_id, neo4j_driver)
        case 'POST':
            return update_student_progress(student_id, event['body'], neo4j_driver)
        case _:
            return {'statusCode': 405, 'body': 'Method not allowed'}
Option B: ECS Containers with Different Python Versions
dockerfile# Dockerfile.trac (Python 2.7)
FROM python:2.7-slim
WORKDIR /app
COPY trac/ .
RUN pip install Trac==1.4.4 psycopg2-binary==2.8.6
CMD ["tracd", "--port", "8000", "/var/trac/projects"]

# Dockerfile.LearnTrac (Python 3.11)
FROM python:3.11-slim
WORKDIR /app
COPY LearnTrac_api/ .
RUN pip install fastapi uvicorn neo4j-driver psycopg2-binary
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
Option C: Hybrid EC2 Setup
bash# On a single EC2 instance, run both Python versions
# Install Python 2.7 and 3.11 side by side
sudo yum install python27 python311

# Run Trac on Python 2.7
/usr/bin/python2.7 -m trac.web.standalone --port 8000

# Run LearnTrac API on Python 3.11
/usr/bin/python3.11 -m uvicorn LearnTrac_api:app --port 8001

# Use Nginx to proxy both
3. Database Bridge Pattern
Since Trac uses Python 2.7 with an old psycopg2, create a database bridge:
python# db_bridge/trac_bridge.py (Python 3.11)
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import redis

class TracDatabaseBridge:
    """Modern Python 3 bridge to Trac's database"""
    
    def __init__(self, db_url):
        # Use modern psycopg2 or psycopg3
        self.conn = psycopg2.connect(db_url)
        self.redis = redis.Redis(host='localhost', port=6379)
    
    async def get_ticket_as_concept(self, ticket_id: int):
        """Get Trac ticket data and transform to learning concept"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.*, 
                       tc.value as custom_value
                FROM ticket t
                LEFT JOIN ticket_custom tc ON t.id = tc.ticket
                WHERE t.id = %s
            """, (ticket_id,))
            
            ticket_data = cur.fetchone()
            
            # Cache in Redis for performance
            self.redis.setex(
                f"ticket:{ticket_id}", 
                3600, 
                json.dumps(ticket_data)
            )
            
            return self.transform_to_concept(ticket_data)
4. AWS Architecture Recommendations
A. Serverless Approach (Cost-Effective)
yaml# serverless.yml for LearnTrac features
service: LearnTrac-api

provider:
  name: aws
  runtime: python3.11
  environment:
    TRAC_DB_URL: ${ssm:/LearnTrac/db_url}
    NEO4J_URL: ${ssm:/LearnTrac/neo4j_url}

functions:
  learning_api:
    handler: handlers/learning.handler
    events:
      - http:
          path: /api/LearnTrac/{proxy+}
          method: ANY
          
  voice_tutor:
    handler: handlers/voice.handler
    timeout: 900  # 15 minutes for voice sessions
    events:
      - websocket:
          route: $connect
          
  ai_chat:
    handler: handlers/chat.handler
    environment:
      OPENAI_API_KEY: ${ssm:/LearnTrac/openai_key}
    events:
      - http:
          path: /api/chat
          method: POST
B. Container-Based Approach (More Control)
yaml# docker-compose.yml for AWS ECS
version: '3.8'

services:
  trac:
    build:
      context: .
      dockerfile: Dockerfile.trac
    environment:
      - PYTHON_VERSION=2.7
      - DATABASE_URL=postgresql://user:pass@rds-endpoint/trac
    ports:
      - "8000:8000"
      
  LearnTrac-api:
    build:
      context: .
      dockerfile: Dockerfile.LearnTrac
    environment:
      - PYTHON_VERSION=3.11
      - DATABASE_URL=postgresql://user:pass@rds-endpoint/trac
      - NEO4J_URL=bolt://neo4j:7687
    ports:
      - "8001:8001"
      
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
C. Gradual Migration Path
python# migration/proxy_adapter.py (Python 3.11)
class LearnTracProxy:
    """Proxy that gradually migrates features from Trac to LearnTrac"""
    
    def __init__(self):
        self.trac_client = TracXMLRPCClient("http://localhost:8000/xmlrpc")
        self.LearnTrac_api = LearnTracAPI()
    
    async def handle_request(self, path: str, method: str, data: dict):
        # New LearnTrac endpoints
        if path.startswith('/api/LearnTrac/'):
            return await self.LearnTrac_api.handle(path, method, data)
            
        # Voice features (Python 3 only)
        elif path.startswith('/voice/'):
            return await self.handle_voice_session(data)
            
        # Legacy Trac endpoints
        else:
            return self.proxy_to_trac(path, method, data)
5. Recommended Architecture for LearnTrac
Given your constraints, here's the recommended approach:
bash# AWS Services Setup
┌─────────────────────────────────────────────────────────────┐
│ Route 53 → CloudFront → ALB                                │
├─────────────────────────────────────────────────────────────┤
│ Application Load Balancer                                   │
│   ├── Target Group 1: Trac (Python 2.7)                   │
│   │   └── ECS Service or EC2 (Port 8000)                  │
│   │                                                        │
│   ├── Target Group 2: LearnTrac API (Python 3.11)         │
│   │   └── Lambda or ECS Service (Port 8001)               │
│   │                                                        │
│   └── Target Group 3: WebSocket/Voice (Python 3.11)       │
│       └── API Gateway WebSocket → Lambda                   │
├─────────────────────────────────────────────────────────────┤
│ Data Layer                                                  │
│   ├── RDS PostgreSQL (Shared by both)                     │
│   ├── ElastiCache Redis (Session/Cache)                   │
│   └── Neptune or Self-Hosted Neo4j (Knowledge Graph)      │
└─────────────────────────────────────────────────────────────┘
6. Implementation Steps
Step 1: Set up the Python 3 API Service
python# LearnTrac_api/main.py (Python 3.11)
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
import aioboto3
import asyncpg

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=10,
        max_size=20
    )
    yield
    # Shutdown
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)

@app.get("/api/LearnTrac/health")
async def health_check():
    return {"status": "healthy", "python_version": "3.11"}

@app.post("/api/LearnTrac/concepts/{concept_id}/practice")
async def practice_concept(concept_id: int, student_id: str = Depends(get_current_user)):
    # Modern Python 3.11 code here
    async with app.state.db_pool.acquire() as conn:
        # Direct database access to Trac's tables
        concept = await conn.fetchrow(
            "SELECT * FROM ticket WHERE id = $1", 
            concept_id
        )
    return {"concept": dict(concept), "status": "practicing"}
Step 2: Configure ALB Path-Based Routing
terraform# alb.tf
resource "aws_lb_listener_rule" "trac_legacy" {
  listener_arn = aws_lb_listener.main.arn
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trac_py27.arn
  }
  
  condition {
    path_pattern {
      values = ["/trac/*", "/ticket/*", "/wiki/*"]
    }
  }
}

resource "aws_lb_listener_rule" "LearnTrac_api" {
  listener_arn = aws_lb_listener.main.arn
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.LearnTrac_py311.arn
  }
  
  condition {
    path_pattern {
      values = ["/api/LearnTrac/*", "/voice/*", "/chat/*"]
    }
  }
}
Step 3: Database Compatibility Layer
python# LearnTrac_api/db/compatibility.py
class TracCompatibilityLayer:
    """Ensures Python 3 code can work with Trac's schema"""
    
    @staticmethod
    async def get_learning_concepts(conn, student_id: str):
        # Read from Trac's tables
        tickets = await conn.fetch("""
            SELECT t.*, 
                   tc.value as custom_value,
                   tc.name as custom_name
            FROM ticket t
            LEFT JOIN ticket_custom tc ON t.id = tc.ticket
            WHERE t.owner = $1 
              AND t.type = 'task'
              AND tc.name IN ('learning_difficulty', 'mastery_threshold')
        """, student_id)
        
        # Transform to modern format
        return [TracCompatibilityLayer.ticket_to_concept(t) for t in tickets]
7. Quick Start Commands
bash# 1. Install Python 2.7 for Trac (if needed)
conda create -n trac_env python=2.7
conda activate trac_env
pip install Trac==1.4.4 psycopg2==2.8.6

# 2. Install Python 3.11 for LearnTrac
conda create -n LearnTrac_env python=3.11
conda activate LearnTrac_env
pip install fastapi uvicorn neo4j psycopg[binary]

# 3. Run both services
# Terminal 1 (Trac)
conda activate trac_env
tracd --port 8000 /path/to/trac/project

# Terminal 2 (LearnTrac API)
conda activate LearnTrac_env
uvicorn LearnTrac_api.main:app --port 8001

# 4. Run Nginx to proxy both
nginx -c /path/to/nginx.conf
This approach allows you to:

Keep Trac running on Python 2.7 without changes
Build all new LearnTrac features in Python 3.11+
Share the same PostgreSQL database
Gradually migrate features if desired
Use modern Python features for AI, voice, and advanced analytics

The key is treating them as separate services that happen to share a database, rather than trying to force Python 3 features into the Python 2.7 environment.RetryHHlet's go forward with this plan. break it down step by step with documentation about how each will need to be configured and how we can leverage terraform to setup what we needEditLearnTrac AWS Infrastructure: Step-by-Step Implementation Guide
Overview
We'll build a dual-Python architecture where Trac runs on Python 2.7 and new LearnTrac features run on Python 3.11+, all managed through Terraform.
Step 1: Project Structure Setup
First, let's organize our project:
bashlearntrac/
├── terraform/
│   ├── environments/
│   │   ├── dev/
│   │   │   ├── terraform.tfvars
│   │   │   └── backend.tf
│   │   └── prod/
│   │       ├── terraform.tfvars
│   │       └── backend.tf
│   ├── modules/
│   │   ├── alb/
│   │   ├── ecs/
│   │   ├── lambda/
│   │   └── rds/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── trac-legacy/
│   ├── Dockerfile
│   ├── requirements.txt (Python 2.7)
│   └── config/
├── LearnTrac-api/
│   ├── Dockerfile
│   ├── requirements.txt (Python 3.11)
│   ├── src/
│   └── tests/
├── nginx/
│   └── nginx.conf
└── scripts/
    ├── deploy.sh
    └── setup-local.sh
Step 2: Terraform Infrastructure Setup
2.1 Main Terraform Configuration
hcl# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# VPC Configuration (using default or custom)
data "aws_vpc" "main" {
  default = var.use_default_vpc
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  
  tags = {
    Tier = "Private"
  }
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  
  tags = {
    Tier = "Public"
  }
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  name_prefix    = local.project_prefix
  vpc_id         = data.aws_vpc.main.id
  subnet_ids     = data.aws_subnets.public.ids
  certificate_arn = var.ssl_certificate_arn
  
  tags = local.common_tags
}

# ECS Cluster for both services
resource "aws_ecs_cluster" "main" {
  name = "${local.project_prefix}-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = local.common_tags
}

# Trac Legacy Service (Python 2.7)
module "trac_service" {
  source = "./modules/ecs"
  
  name_prefix      = "${local.project_prefix}-trac"
  cluster_id       = aws_ecs_cluster.main.id
  vpc_id           = data.aws_vpc.main.id
  subnet_ids       = data.aws_subnets.private.ids
  
  container_image  = "${aws_ecr_repository.trac.repository_url}:latest"
  container_port   = 8000
  cpu              = 512
  memory           = 1024
  
  environment_variables = {
    TRAC_ENV         = "/var/trac/projects"
    DATABASE_URL     = "postgres://${var.db_username}:${data.aws_ssm_parameter.db_password.value}@${module.rds.endpoint}/${var.db_name}"
    PYTHON_VERSION   = "2.7"
  }
  
  target_group_arn = module.alb.trac_target_group_arn
  
  tags = local.common_tags
}

# LearnTrac API Service (Python 3.11)
module "LearnTrac_service" {
  source = "./modules/ecs"
  
  name_prefix      = "${local.project_prefix}-LearnTrac"
  cluster_id       = aws_ecs_cluster.main.id
  vpc_id           = data.aws_vpc.main.id
  subnet_ids       = data.aws_subnets.private.ids
  
  container_image  = "${aws_ecr_repository.LearnTrac.repository_url}:latest"
  container_port   = 8001
  cpu              = 1024
  memory           = 2048
  
  environment_variables = {
    DATABASE_URL     = "postgresql+asyncpg://${var.db_username}:${data.aws_ssm_parameter.db_password.value}@${module.rds.endpoint}/${var.db_name}"
    REDIS_URL        = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    NEO4J_URL        = var.neo4j_url
    PYTHON_VERSION   = "3.11"
  }
  
  target_group_arn = module.alb.LearnTrac_target_group_arn
  
  tags = local.common_tags
}

# Lambda Functions for specific features
module "voice_lambda" {
  source = "./modules/lambda"
  
  function_name    = "${local.project_prefix}-voice-handler"
  runtime          = "python3.11"
  handler          = "voice_handler.lambda_handler"
  source_path      = "../LearnTrac-api/lambdas/voice"
  
  environment_variables = {
    DATABASE_URL = "postgresql://${var.db_username}:${data.aws_ssm_parameter.db_password.value}@${module.rds.endpoint}/${var.db_name}"
  }
  
  tags = local.common_tags
}
2.2 ALB Module with Path-Based Routing
hcl# terraform/modules/alb/main.tf
resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnet_ids
  
  enable_deletion_protection = var.environment == "prod"
  enable_http2              = true
  
  tags = var.tags
}

resource "aws_security_group" "alb" {
  name_prefix = "${var.name_prefix}-alb-sg"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = var.tags
}

# Target Groups
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
  
  tags = var.tags
}

resource "aws_lb_target_group" "LearnTrac" {
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
    path                = "/api/LearnTrac/health"
    port                = "traffic-port"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  tags = var.tags
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
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

# HTTP Listener (redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Path-based routing rules
resource "aws_lb_listener_rule" "trac_paths" {
  listener_arn = aws_lb_listener.https.arn
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
        "/roadmap/*",
        "/browser/*",
        "/changeset/*",
        "/attachment/*",
        "/login",
        "/logout"
      ]
    }
  }
}

resource "aws_lb_listener_rule" "LearnTrac_api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 90
  
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.LearnTrac.arn
  }
  
  condition {
    path_pattern {
      values = [
        "/api/LearnTrac/*",
        "/api/chat/*",
        "/api/voice/*",
        "/api/analytics/*"
      ]
    }
  }
}

resource "aws_lb_listener_rule" "static_assets" {
  listener_arn = aws_lb_listener.https.arn
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
        "*.png",
        "*.jpg",
        "*.ico"
      ]
    }
  }
}

# Outputs
output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "trac_target_group_arn" {
  value = aws_lb_target_group.trac.arn
}

output "LearnTrac_target_group_arn" {
  value = aws_lb_target_group.LearnTrac.arn
}
2.3 ECS Module for Container Services
hcl# terraform/modules/ecs/main.tf
resource "aws_ecs_task_definition" "main" {
  family                   = var.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name      = "app"
      image     = var.container_image
      cpu       = var.cpu
      memory    = var.memory
      essential = true
      
      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]
      
      environment = [
        for key, value in var.environment_variables : {
          name  = key
          value = value
        }
      ]
      
      secrets = [
        for key, value in var.secret_variables : {
          name      = key
          valueFrom = value
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.main.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
  
  tags = var.tags
}

resource "aws_ecs_service" "main" {
  name                               = var.name_prefix
  cluster                            = var.cluster_id
  task_definition                    = aws_ecs_task_definition.main.arn
  desired_count                      = var.desired_count
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200
  launch_type                        = "FARGATE"
  scheduling_strategy                = "REPLICA"
  
  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = var.subnet_ids
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.container_port
  }
  
  lifecycle {
    ignore_changes = [desired_count]
  }
  
  depends_on = [var.target_group_arn]
}

# Auto Scaling
resource "aws_appautoscaling_target" "main" {
  max_capacity       = var.max_count
  min_capacity       = var.min_count
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.name_prefix}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.main.resource_id
  scalable_dimension = aws_appautoscaling_target.main.scalable_dimension
  service_namespace  = aws_appautoscaling_target.main.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Security Group
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.name_prefix}-ecs-tasks-sg"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = var.alb_security_group_ids
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = var.tags
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = var.log_retention_days
  
  tags = var.tags
}

# IAM Roles
resource "aws_iam_role" "ecs_execution" {
  name_prefix = "${var.name_prefix}-ecs-execution-"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name_prefix = "${var.name_prefix}-ecs-task-"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}
Step 3: Container Configurations
3.1 Trac Legacy Container (Python 2.7)
dockerfile# trac-legacy/Dockerfile
FROM python:2.7-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    git \
    subversion \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Trac configuration
COPY config/ /etc/trac/

# Copy custom Trac plugins if any
COPY plugins/ /usr/local/lib/python2.7/site-packages/

# Create Trac environment directory
RUN mkdir -p /var/trac/projects

# Copy startup script
COPY scripts/start-trac.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-trac.sh

# Expose port
EXPOSE 8000

# Start Trac
CMD ["/usr/local/bin/start-trac.sh"]
txt# trac-legacy/requirements.txt
Trac==1.4.4
psycopg2==2.8.6
Genshi==0.7.7
Babel==2.9.1
Pygments==2.5.2
pytz
bash#!/bin/bash
# trac-legacy/scripts/start-trac.sh

# Initialize Trac environment if it doesn't exist
if [ ! -f "/var/trac/projects/VERSION" ]; then
    echo "Initializing Trac environment..."
    trac-admin /var/trac/projects initenv "LearnTrac" "${DATABASE_URL}" git /var/git/repos
fi

# Upgrade Trac database
trac-admin /var/trac/projects upgrade

# Deploy static resources
trac-admin /var/trac/projects deploy /tmp/deploy

# Start Trac using the standalone server
exec tracd --port 8000 \
    --auth="*,/etc/trac/htpasswd,LearnTrac" \
    /var/trac/projects
3.2 LearnTrac API Container (Python 3.11)
dockerfile# LearnTrac-api/Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Run database migrations on startup
COPY scripts/start-api.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-api.sh

# Expose port
EXPOSE 8001

# Start API
CMD ["/usr/local/bin/start-api.sh"]
txt# LearnTrac-api/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg[binary,pool]==3.1.12
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.23
alembic==1.12.1
redis==5.0.1
neo4j==5.14.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
boto3==1.29.7
aioboto3==12.1.0
openai==1.3.7
numpy==1.26.2
pandas==2.1.3
sentence-transformers==2.2.2
python# LearnTrac-api/src/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
from redis import asyncio as aioredis
from neo4j import AsyncGraphDatabase
import logging

from .config import settings
from .routers import learning, chat, analytics, voice
from .middleware import TimingMiddleware, AuthMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting LearnTrac API...")
    
    # Initialize database pool
    app.state.db_pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=10,
        max_size=20,
        command_timeout=60
    )
    
    # Initialize Redis
    app.state.redis = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Initialize Neo4j
    app.state.neo4j = AsyncGraphDatabase.driver(
        settings.neo4j_url,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    
    logger.info("LearnTrac API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LearnTrac API...")
    await app.state.db_pool.close()
    await app.state.redis.close()
    await app.state.neo4j.close()

app = FastAPI(
    title="LearnTrac API",
    description="Modern learning features for Trac",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(TimingMiddleware)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(learning.router, prefix="/api/LearnTrac", tags=["learning"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        async with app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis
        await app.state.redis.ping()
        
        # Check Neo4j
        async with app.state.neo4j.session() as session:
            await session.run("RETURN 1")
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "python_version": "3.11"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/api/LearnTrac/health")
async def api_health():
    """LearnTrac-specific health check"""
    return {
        "status": "healthy",
        "service": "LearnTrac-api",
        "features": {
            "learning": "enabled",
            "chat": "enabled",
            "voice": "enabled",
            "analytics": "enabled"
        }
    }
Step 4: Database Bridge Implementation
python# LearnTrac-api/src/db/trac_bridge.py
"""
Bridge between modern Python 3.11 code and Trac's database schema
"""
import asyncpg
from typing import List, Dict, Optional
from datetime import datetime
import json

class TracDatabaseBridge:
    """Provides modern async interface to Trac's database"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_ticket_as_concept(self, ticket_id: int) -> Optional[Dict]:
        """Transform Trac ticket into learning concept"""
        async with self.db_pool.acquire() as conn:
            # Get base ticket data
            ticket = await conn.fetchrow("""
                SELECT 
                    id, type, time, changetime, component, severity,
                    priority, owner, reporter, cc, version, milestone,
                    status, resolution, summary, description, keywords
                FROM ticket
                WHERE id = $1
            """, ticket_id)
            
            if not ticket:
                return None
            
            # Get custom fields
            custom_fields = await conn.fetch("""
                SELECT name, value
                FROM ticket_custom
                WHERE ticket = $1
            """, ticket_id)
            
            # Transform to learning concept
            concept = dict(ticket)
            concept['custom_fields'] = {
                field['name']: field['value'] 
                for field in custom_fields
            }
            
            # Extract learning-specific fields
            concept['learning_difficulty'] = float(
                concept['custom_fields'].get('learning_difficulty', '2.0')
            )
            concept['mastery_threshold'] = float(
                concept['custom_fields'].get('mastery_threshold', '0.8')
            )
            concept['prerequisites'] = json.loads(
                concept['custom_fields'].get('prerequisite_concepts', '[]')
            )
            
            return concept
    
    async def update_ticket_learning_status(
        self, 
        ticket_id: int, 
        student_id: str,
        status: str,
        **kwargs
    ):
        """Update ticket with learning progress"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Update ticket status
                await conn.execute("""
                    UPDATE ticket 
                    SET status = $1, changetime = $2
                    WHERE id = $3
                """, status, int(datetime.now().timestamp()), ticket_id)
                
                # Add to ticket_change history
                await conn.execute("""
                    INSERT INTO ticket_change 
                    (ticket, time, author, field, oldvalue, newvalue)
                    VALUES ($1, $2, $3, 'status', 
                        (SELECT status FROM ticket WHERE id = $1), $4)
                """, ticket_id, int(datetime.now().timestamp()), 
                    student_id, status)
                
                # Update custom fields
                for field, value in kwargs.items():
                    await conn.execute("""
                        INSERT INTO ticket_custom (ticket, name, value)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (ticket, name) 
                        DO UPDATE SET value = EXCLUDED.value
                    """, ticket_id, field, str(value))
    
    async def get_student_tickets(
        self, 
        student_id: str,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get all tickets assigned to a student"""
        query = """
            SELECT t.*, 
                   array_agg(
                       json_build_object('name', tc.name, 'value', tc.value)
                   ) as custom_fields
            FROM ticket t
            LEFT JOIN ticket_custom tc ON t.id = tc.ticket
            WHERE t.owner = $1
        """
        
        params = [student_id]
        
        if status_filter:
            query += " AND t.status = ANY($2)"
            params.append(status_filter)
        
        query += " GROUP BY t.id"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_milestone_progress(self, milestone: str) -> Dict:
        """Get learning progress for a milestone"""
        async with self.db_pool.acquire() as conn:
            # Get all tickets in milestone
            tickets = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM ticket
                WHERE milestone = $1
                GROUP BY status
            """, milestone)
            
            total = sum(t['count'] for t in tickets)
            completed = sum(
                t['count'] for t in tickets 
                if t['status'] in ('closed', 'mastered')
            )
            
            return {
                'milestone': milestone,
                'total_concepts': total,
                'completed_concepts': completed,
                'progress_percentage': (completed / total * 100) if total > 0 else 0,
                'status_breakdown': {
                    t['status']: t['count'] for t in tickets
                }
            }
Step 5: Supporting Services Setup
5.1 Redis for Session Management
hcl# terraform/redis.tf
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.project_prefix}-redis-subnet"
  subnet_ids = data.aws_subnets.private.ids
  
  tags = local.common_tags
}

resource "aws_security_group" "redis" {
  name_prefix = "${local.project_prefix}-redis-sg"
  vpc_id      = data.aws_vpc.main.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [
      module.trac_service.security_group_id,
      module.LearnTrac_service.security_group_id
    ]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = local.common_tags
}

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
  
  tags = local.common_tags
}
5.2 API Gateway for WebSocket Support
hcl# terraform/api_gateway.tf
resource "aws_apigatewayv2_api" "websocket" {
  name                       = "${local.project_prefix}-websocket"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
  
  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "websocket" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = var.environment
  auto_deploy = true
  
  default_route_settings {
    throttle_rate_limit  = 10000
    throttle_burst_limit = 5000
  }
  
  tags = local.common_tags
}

# Routes for voice chat
resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.connect.id}"
}

resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.disconnect.id}"
}

resource "aws_apigatewayv2_route" "voice" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "voice"
  target    = "integrations/${aws_apigatewayv2_integration.voice.id}"
}

# Lambda integrations
resource "aws_apigatewayv2_integration" "connect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.voice_lambda.connect_invoke_arn
}

resource "aws_apigatewayv2_integration" "disconnect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.voice_lambda.disconnect_invoke_arn
}

resource "aws_apigatewayv2_integration" "voice" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = module.voice_lambda.voice_invoke_arn
}
Step 6: Deployment Scripts
6.1 Deployment Script
bash#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-dev}
ACTION=${2:-apply}

echo "Deploying LearnTrac to $ENVIRONMENT environment..."

# Build and push Docker images
echo "Building Docker images..."

# Build Trac image
docker build -t LearnTrac-trac:latest ./trac-legacy/
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag LearnTrac-trac:latest $ECR_REGISTRY/LearnTrac-trac:latest
docker push $ECR_REGISTRY/LearnTrac-trac:latest

# Build LearnTrac API image
docker build -t LearnTrac-api:latest ./LearnTrac-api/
docker tag LearnTrac-api:latest $ECR_REGISTRY/LearnTrac-api:latest
docker push $ECR_REGISTRY/LearnTrac-api:latest

# Deploy infrastructure
cd terraform/environments/$ENVIRONMENT
terraform init
terraform $ACTION -auto-approve

# Update ECS services to use new images
if [ "$ACTION" == "apply" ]; then
    aws ecs update-service \
        --cluster LearnTrac-$ENVIRONMENT-cluster \
        --service LearnTrac-$ENVIRONMENT-trac \
        --force-new-deployment
    
    aws ecs update-service \
        --cluster LearnTrac-$ENVIRONMENT-cluster \
        --service LearnTrac-$ENVIRONMENT-LearnTrac \
        --force-new-deployment
fi

echo "Deployment complete!"
6.2 Local Development Setup
bash#!/bin/bash
# scripts/setup-local.sh

set -e

echo "Setting up local LearnTrac development environment..."

# Create Python 2.7 environment for Trac
echo "Creating Python 2.7 environment for Trac..."
conda create -n trac_env python=2.7 -y
conda activate trac_env
pip install -r trac-legacy/requirements.txt

# Create Python 3.11 environment for LearnTrac
echo "Creating Python 3.11 environment for LearnTrac API..."
conda deactivate
conda create -n LearnTrac_env python=3.11 -y
conda activate LearnTrac_env
pip install -r LearnTrac-api/requirements.txt

# Start PostgreSQL locally
echo "Starting PostgreSQL..."
docker run -d \
    --name LearnTrac-postgres \
    -e POSTGRES_PASSWORD=localpass \
    -e POSTGRES_DB=LearnTrac \
    -p 5432:5432 \
    postgres:15

# Start Redis locally
echo "Starting Redis..."
docker run -d \
    --name LearnTrac-redis \
    -p 6379:6379 \
    redis:7-alpine

# Start Neo4j locally
echo "Starting Neo4j..."
docker run -d \
    --name LearnTrac-neo4j \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/LearnTrac123 \
    neo4j:5-community

echo "Local environment setup complete!"
echo ""
echo "To start Trac (Python 2.7):"
echo "  conda activate trac_env"
echo "  python -m trac.web.standalone --port 8000 /path/to/trac/env"
echo ""
echo "To start LearnTrac API (Python 3.11):"
echo "  conda activate LearnTrac_env"
echo "  cd LearnTrac-api"
echo "  uvicorn src.main:app --reload --port 8001"
Step 7: Environment Configuration
7.1 Development Environment
hcl# terraform/environments/dev/terraform.tfvars
aws_region           = "us-east-2"
project_name         = "LearnTrac"
environment          = "dev"
use_default_vpc      = true

# ECS Configuration
trac_cpu             = 512
trac_memory          = 1024
trac_desired_count   = 1

LearnTrac_cpu        = 1024
LearnTrac_memory     = 2048
LearnTrac_desired_count = 1

# RDS Configuration
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20

# Redis Configuration
redis_node_type      = "cache.t3.micro"

# External services
neo4j_url           = "neo4j+s://your-neo4j-instance.databases.neo4j.io"
7.2 Production Environment
hcl# terraform/environments/prod/terraform.tfvars
aws_region           = "us-east-2"
project_name         = "LearnTrac"
environment          = "prod"
use_default_vpc      = false
vpc_id              = "vpc-xxxxxxxxx"

# ECS Configuration
trac_cpu             = 2048
trac_memory          = 4096
trac_desired_count   = 2
trac_min_count      = 2
trac_max_count      = 10

LearnTrac_cpu        = 4096
LearnTrac_memory     = 8192
LearnTrac_desired_count = 3
LearnTrac_min_count  = 3
LearnTrac_max_count  = 20

# RDS Configuration
db_instance_class    = "db.r6g.xlarge"
db_allocated_storage = 100
db_multi_az         = true
db_backup_retention  = 30

# Redis Configuration
redis_node_type      = "cache.r6g.large"

# External services
neo4j_url           = "neo4j+s://prod-neo4j.databases.neo4j.io"
ssl_certificate_arn  = "arn:aws:acm:us-east-2:xxx:certificate/xxx"
Step 8: Monitoring and Observability
hcl# terraform/monitoring.tf
resource "aws_cloudwatch_dashboard" "LearnTrac" {
  dashboard_name = "${local.project_prefix}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${local.project_prefix}-trac"],
            [".", ".", ".", "${local.project_prefix}-LearnTrac"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "ECS CPU Utilization"
        }
      },
      {
        type   = "metric"
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix]
          ]
          period = 60
          stat   = "Average"
          region = var.aws_region
          title  = "ALB Response Time"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "${local.project_prefix}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  
  dimensions = {
    ServiceName = "${local.project_prefix}-LearnTrac"
    ClusterName = aws_ecs_cluster.main.name
  }
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}
Summary
This setup provides:

Complete isolation between Python 2.7 (Trac) and Python 3.11 (LearnTrac)
Path-based routing via ALB to direct traffic appropriately
Shared database access with compatibility layer
Modern features in Python 3.11 without touching legacy code
Scalable architecture using ECS Fargate
Full infrastructure as code with Terraform

The architecture allows you to run Trac unchanged while building new features with modern Python, eventually enabling a gradual migration if desired.