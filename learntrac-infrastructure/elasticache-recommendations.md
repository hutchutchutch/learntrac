# ElastiCache Redis Configuration Recommendations

## Production-Ready Configuration Template

Based on the validation of the current development setup, here are the recommended configurations for different environments:

### Development Environment (Current)
```hcl
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.project_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  snapshot_retention_limit = 0
  
  # Current configuration is appropriate for development
}
```

### Staging Environment
```hcl
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.project_prefix}-redis"
  replication_group_description = "Redis cluster for LearnTrac staging"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.t3.small"
  number_cache_clusters = 2  # Primary + 1 replica
  
  parameter_group_name = aws_elasticache_parameter_group.redis_staging.name
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  snapshot_retention_limit = 3
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:06:00"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false  # Enable if app supports it
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }
  
  tags = merge(local.common_tags, {
    Environment = "staging"
  })
}

resource "aws_elasticache_parameter_group" "redis_staging" {
  family = "redis7"
  name   = "${local.project_prefix}-redis-params-staging"
  
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }
}
```

### Production Environment
```hcl
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.project_prefix}-redis"
  replication_group_description = "Redis cluster for LearnTrac production"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.m6g.large"  # Or cache.r6g.large for memory-intensive
  number_cache_clusters = 3  # Primary + 2 replicas
  
  parameter_group_name = aws_elasticache_parameter_group.redis_prod.name
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:06:00"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled        = true
  
  # Enable backups
  snapshot_retention_limit = 7
  final_snapshot_identifier = "${local.project_prefix}-redis-final-snapshot"
  
  # CloudWatch Logs
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_engine_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "engine-log"
  }
  
  notification_topic_arn = aws_sns_topic.redis_notifications.arn
  
  tags = merge(local.common_tags, {
    Environment = "production"
    Backup      = "daily"
    Critical    = "true"
  })
}

resource "aws_elasticache_parameter_group" "redis_prod" {
  family = "redis7"
  name   = "${local.project_prefix}-redis-params-prod"
  
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }
  
  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }
  
  parameter {
    name  = "slowlog-log-slower-than"
    value = "10000"  # Log queries slower than 10ms
  }
  
  parameter {
    name  = "slowlog-max-len"
    value = "128"
  }
  
  parameter {
    name  = "latency-monitor-threshold"
    value = "100"  # Monitor latency above 100ms
  }
}
```

## CloudWatch Alarms Configuration

### Critical Alarms (Production)
```hcl
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${local.project_prefix}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Redis CPU utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_high" {
  alarm_name          = "${local.project_prefix}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "90"
  alarm_description   = "Redis memory usage is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${local.project_prefix}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1000"
  alarm_description   = "Redis is evicting keys due to memory pressure"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${local.project_prefix}-redis-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000"  # Adjust based on your needs
  alarm_description   = "Redis connection count is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }
}
```

## Application Configuration Best Practices

### Connection Pool Settings
```python
# Python Redis connection pool configuration
import redis
from redis.sentinel import Sentinel

# For single-node Redis (dev)
redis_pool = redis.ConnectionPool(
    host='redis-endpoint',
    port=6379,
    max_connections=50,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 60, # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    },
    decode_responses=True
)

# For Redis with replicas (staging/prod)
sentinels = [('sentinel1', 26379), ('sentinel2', 26379)]
sentinel = Sentinel(sentinels)
redis_master = sentinel.master_for('mymaster', socket_timeout=0.1)
redis_slave = sentinel.slave_for('mymaster', socket_timeout=0.1)
```

### Session Management Configuration
```python
# Django settings for Redis sessions
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': False,  # Set to True in production
        },
        'KEY_PREFIX': 'learntrac',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
```

## Key Naming Conventions

### Recommended Key Structure
```
{app}:{module}:{entity}:{identifier}

Examples:
- learntrac:session:user:12345
- learntrac:cache:course:cs101
- learntrac:queue:notifications:high
- learntrac:temp:upload:abc123
```

### TTL Strategy
```python
# Define TTL constants
TTL_SESSION = 86400      # 24 hours
TTL_CACHE_SHORT = 300    # 5 minutes
TTL_CACHE_MEDIUM = 3600  # 1 hour
TTL_CACHE_LONG = 86400   # 24 hours
TTL_TEMP = 300           # 5 minutes

# Usage example
redis_client.setex(
    f"learntrac:cache:user:{user_id}",
    TTL_CACHE_MEDIUM,
    json.dumps(user_data)
)
```

## Monitoring Dashboard Queries

### CloudWatch Insights Queries
```sql
-- Top slow queries
fields @timestamp, @message
| filter @message like /slowlog/
| stats count() by bin(5m)

-- Connection patterns
fields @timestamp, connected_clients
| filter @type = "metric"
| stats avg(connected_clients), max(connected_clients) by bin(5m)

-- Memory usage trends
fields @timestamp, used_memory_rss, used_memory
| filter @type = "metric"
| stats avg(used_memory_rss), avg(used_memory) by bin(1h)
```

## Cost Optimization Tips

### 1. Reserved Instances
- Save up to 55% with 1-year reserved instances
- Save up to 75% with 3-year reserved instances

### 2. Right-Sizing
- Monitor actual usage and adjust instance types
- Use CloudWatch metrics to identify underutilized resources

### 3. Data Optimization
- Implement proper TTLs to prevent unbounded growth
- Use compression for large values
- Consider Redis data structures (HyperLogLog, Bitmaps) for specific use cases

### 4. Multi-Purpose Usage
- Leverage Redis for multiple purposes:
  - Session storage
  - Application cache
  - Rate limiting
  - Pub/Sub messaging
  - Queues (with reliability considerations)

## Migration Checklist

### From Development to Production
- [ ] Enable Multi-AZ deployment
- [ ] Configure automatic failover
- [ ] Enable encryption at rest and in transit
- [ ] Set up automated backups with appropriate retention
- [ ] Create custom parameter group with optimized settings
- [ ] Configure CloudWatch alarms for all critical metrics
- [ ] Implement connection pooling in applications
- [ ] Test failover scenarios
- [ ] Document runbooks for common issues
- [ ] Set up monitoring dashboards
- [ ] Configure SNS notifications for critical events
- [ ] Review and optimize slow queries
- [ ] Implement proper key naming conventions
- [ ] Configure appropriate TTLs for all key types
- [ ] Load test with expected production traffic