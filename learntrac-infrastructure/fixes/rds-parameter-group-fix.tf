# Fixed RDS Parameter Group Configuration

resource "aws_db_parameter_group" "learntrac_pg15" {
  name        = "${local.project_prefix}-pg15-params"
  family      = "postgres15"
  description = "Custom parameter group for LearnTrac PostgreSQL 15"

  # Connection settings - Dynamic parameter
  parameter {
    name         = "max_connections"
    value        = var.environment == "prod" ? "200" : "100"
    apply_method = "immediate"
  }

  # Memory settings - Static parameters require pending-reboot
  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/4}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "immediate"
  }

  parameter {
    name         = "work_mem"
    value        = "4096"
    apply_method = "immediate"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "65536"
    apply_method = "immediate"
  }

  # Query optimization
  parameter {
    name         = "random_page_cost"
    value        = "1.1"
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_io_concurrency"
    value        = "200"
    apply_method = "immediate"
  }

  # Logging for troubleshooting
  parameter {
    name         = "log_statement"
    value        = var.environment == "prod" ? "mod" : "all"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = var.environment == "prod" ? "1000" : "500"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_disconnections"
    value        = "1"
    apply_method = "immediate"
  }

  # Enable query performance insights - Static parameter
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "pg_stat_statements.track"
    value        = "all"
    apply_method = "immediate"
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_prefix}-parameter-group"
  })
}