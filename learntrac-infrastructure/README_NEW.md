# LearnTrac Infrastructure

This directory contains the Terraform infrastructure code for LearnTrac - a dual-Python architecture system where Trac runs on Python 2.7 and new LearnTrac features run on Python 3.11+.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   AWS Architecture                   │
├─────────────────────────────────────────────────────┤
│  ALB (Application Load Balancer)                     │
│     ├── /trac/* → ECS Trac Service (Python 2.7)    │
│     ├── /api/learntrac/* → ECS LearnTrac (Python 3.11)│
│     └── /static/* → Trac Static Assets             │
├─────────────────────────────────────────────────────┤
│  Data Layer                                          │
│     ├── RDS PostgreSQL (Shared Database)           │
│     ├── ElastiCache Redis (Session Management)     │
│     └── Neo4j (Optional - Knowledge Graph)         │
└─────────────────────────────────────────────────────┘
```

## Directory Structure

```
learntrac-infrastructure/
├── modules/              # Reusable Terraform modules
│   ├── alb/             # Application Load Balancer
│   ├── ecs/             # ECS Service configuration
│   ├── lambda/          # Lambda functions (future)
│   └── monitoring/      # CloudWatch dashboards (future)
├── environments/        # Environment-specific configs
│   ├── dev/            # Development settings
│   └── prod/           # Production settings
├── main.tf             # Main Terraform configuration
├── variables.tf        # Variable definitions
├── outputs.tf          # Output values
├── ecr.tf             # ECR repositories
├── ecs.tf             # ECS cluster and services
└── redis.tf           # ElastiCache Redis
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Docker** installed and running
3. **Terraform** >= 1.0
4. **AWS Account** with appropriate permissions

## Quick Start

### 1. Local Development

```bash
# Set up local development environment
cd /path/to/learntrac
./scripts/setup-local.sh

# This will start:
# - PostgreSQL on port 5432
# - Redis on port 6379
# - Neo4j on ports 7474/7687 (optional)
```

### 2. Deploy to AWS

```bash
# Deploy to development environment
./scripts/deploy.sh dev apply

# Deploy to production
./scripts/deploy.sh prod apply

# Destroy infrastructure
./scripts/deploy.sh dev destroy
```

## Module Documentation

### ALB Module

Manages the Application Load Balancer with path-based routing:

- **Trac paths**: `/trac/*`, `/ticket/*`, `/wiki/*`, etc.
- **LearnTrac API**: `/api/learntrac/*`, `/api/chat/*`, `/api/voice/*`
- **Static assets**: `*.css`, `*.js`, `*.png`, etc.

### ECS Module

Reusable module for ECS services with:

- Fargate launch type
- Auto-scaling based on CPU and memory
- CloudWatch logging
- Security group management

### Usage Example

```hcl
module "my_service" {
  source = "./modules/ecs"
  
  name_prefix     = "my-service"
  container_image = "my-image:latest"
  container_port  = 8080
  cpu            = 1024
  memory         = 2048
  
  # ... other configuration
}
```

## Configuration Variables

### Core Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | `us-east-2` |
| `environment` | Environment name | `dev` |
| `project_name` | Project name | `learntrac` |
| `owner_prefix` | Owner prefix for naming | `hutch` |

### ECS Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `trac_cpu` | CPU units for Trac | `512` |
| `trac_memory` | Memory for Trac (MB) | `1024` |
| `learntrac_cpu` | CPU units for LearnTrac | `1024` |
| `learntrac_memory` | Memory for LearnTrac (MB) | `2048` |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `db_instance_class` | RDS instance type | `db.t3.micro` |
| `db_allocated_storage` | Storage in GB | `20` |
| `redis_node_type` | ElastiCache node type | `cache.t3.micro` |

## Outputs

After deployment, Terraform will output:

- `alb_dns_name` - DNS name of the load balancer
- `service_urls` - URLs for accessing services
- `ecr_repository_urls` - Docker registry URLs
- `rds_endpoint` - Database connection endpoint

## Security Considerations

1. **Database Access**: RDS is configured to allow access only from specific IPs
2. **Secrets Management**: Database passwords stored in AWS Secrets Manager
3. **Network Isolation**: ECS tasks run in private subnets
4. **HTTPS**: Support for SSL certificates via ACM

## Monitoring

- ECS Container Insights enabled
- CloudWatch logs for all services
- Auto-scaling based on CPU/memory metrics

## Cost Optimization

- Development uses minimal instance sizes
- Production uses auto-scaling to handle load
- ECR lifecycle policies to limit stored images

## Troubleshooting

### Common Issues

1. **Docker build fails**
   - Ensure Docker daemon is running
   - Check Docker disk space

2. **Terraform apply fails**
   - Verify AWS credentials
   - Check terraform state consistency

3. **ECS service won't start**
   - Check CloudWatch logs
   - Verify security group rules
   - Ensure health check paths are correct

### Viewing Logs

```bash
# View ECS service logs
aws logs tail /ecs/hutch-learntrac-dev-trac --follow
aws logs tail /ecs/hutch-learntrac-dev-learntrac --follow
```

## Future Enhancements

- [ ] Lambda functions for voice/chat features
- [ ] API Gateway WebSocket for real-time communication
- [ ] CloudWatch dashboards and alarms
- [ ] GitHub Actions for CI/CD
- [ ] AWS WAF for additional security

## Contributing

1. Make changes in a feature branch
2. Test in development environment
3. Update documentation
4. Submit pull request

## License

[Your License Here]