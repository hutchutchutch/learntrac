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