variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "owner_prefix" {
  description = "Owner prefix for all resources"
  type        = string
  default     = "hutch"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "learntrac"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "db_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "learntrac_admin"
}

variable "allowed_ip" {
  description = "Your IP address for database access"
  type        = string
  default     = "162.206.172.65"
}

variable "owner_email" {
  description = "Email of the resource owner"
  type        = string
  default     = "hutchenbach@gmail.com"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.7"  # Latest stable 15.x version
}

# SSL Certificate
variable "ssl_certificate_arn" {
  description = "ARN of SSL certificate for HTTPS"
  type        = string
  default     = ""
}

# ECS Configuration for Trac
variable "trac_cpu" {
  description = "CPU units for Trac service"
  type        = number
  default     = 512
}

variable "trac_memory" {
  description = "Memory for Trac service"
  type        = number
  default     = 1024
}

variable "trac_desired_count" {
  description = "Desired number of Trac tasks"
  type        = number
  default     = 1
}

variable "trac_min_count" {
  description = "Minimum number of Trac tasks"
  type        = number
  default     = 1
}

variable "trac_max_count" {
  description = "Maximum number of Trac tasks"
  type        = number
  default     = 4
}

# ECS Configuration for LearnTrac
variable "learntrac_cpu" {
  description = "CPU units for LearnTrac service"
  type        = number
  default     = 1024
}

variable "learntrac_memory" {
  description = "Memory for LearnTrac service"
  type        = number
  default     = 2048
}

variable "learntrac_desired_count" {
  description = "Desired number of LearnTrac tasks"
  type        = number
  default     = 1
}

variable "learntrac_min_count" {
  description = "Minimum number of LearnTrac tasks"
  type        = number
  default     = 1
}

variable "learntrac_max_count" {
  description = "Maximum number of LearnTrac tasks"
  type        = number
  default     = 4
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

# Neo4j Configuration
variable "neo4j_uri" {
  description = "Neo4j database URI (e.g., neo4j+s://xxxx.databases.neo4j.io)"
  type        = string
  default     = ""
}

variable "neo4j_username" {
  description = "Neo4j username"
  type        = string
  default     = "neo4j"
  sensitive   = true
}

variable "neo4j_password" {
  description = "Neo4j password"
  type        = string
  default     = ""
  sensitive   = true
}

# OpenAI Configuration
variable "openai_api_key" {
  description = "OpenAI API key for AI features"
  type        = string
  default     = ""
  sensitive   = true
}