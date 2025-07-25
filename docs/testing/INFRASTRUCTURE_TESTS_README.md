# Infrastructure Validation Test Suite

This comprehensive test suite validates the complete AWS infrastructure configuration for the LearnTrac project, ensuring all components from Task 1 "Update AWS Infrastructure Configuration" are properly implemented.

## Overview

The test suite validates all 10 subtasks of the infrastructure update task:

1. **Terraform Configuration Audit** - Validates .tf files and state management
2. **Cognito User Pool** - Tests authentication configuration
3. **API Gateway** - Verifies API routes and Cognito integration
4. **RDS PostgreSQL** - Checks database connectivity and version
5. **ElastiCache Redis** - Tests cache cluster availability
6. **Trac Database Schema** - Validates all Trac tables exist
7. **Learning Schema** - Confirms learning namespace and tables
8. **VPC & Security Groups** - Tests network configuration
9. **Terraform State** - Validates backend and locking
10. **Documentation** - Checks for required documentation

## Directory Structure

```
docs/testing/infra_tests/
├── config.sh                    # Central configuration file
├── run_all_infra_tests.sh      # Master test runner
├── utils/
│   └── common.sh               # Shared utility functions
└── suites/
    ├── test_terraform.sh       # Subtasks 1.1 & 1.9
    ├── test_cognito.sh         # Subtask 1.2
    ├── test_apigw.sh           # Subtask 1.3
    ├── test_rds.sh             # Subtasks 1.4 & 1.6
    ├── test_redis.sh           # Subtask 1.5
    ├── test_learning_schema.sh # Subtask 1.7
    ├── test_network.sh         # Subtask 1.8
    └── test_docs.sh            # Subtask 1.10
```

## Prerequisites

### Required Tools

- **AWS CLI** - Configured with appropriate credentials
- **jq** - JSON processing utility
- **PostgreSQL client** (psql) - For RDS tests
- **Redis client** (redis-cli) - For ElastiCache tests (optional)
- **Terraform** - For configuration validation

### Required Permissions

The AWS credentials used must have read access to:
- EC2 (VPC, Subnets, Security Groups, Network ACLs)
- RDS (Database instances)
- ElastiCache (Cache clusters)
- Cognito (User pools, clients)
- API Gateway (REST APIs, resources, methods)
- S3 (Terraform state bucket)
- DynamoDB (Terraform lock table)

## Configuration

### Environment Variables

Create a `.env.test` file in the project root or export these variables:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=default

# Terraform Configuration
export TF_DIR=./learntrac-infrastructure
export TF_STATE_BUCKET=learntrac-terraform-state
export TF_STATE_KEY=infrastructure/terraform.tfstate
export TF_LOCK_TABLE=learntrac-terraform-locks

# Cognito Configuration
export COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
export COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
export COGNITO_DOMAIN=learntrac-auth

# API Gateway Configuration
export API_GATEWAY_ID=xxxxxxxxxx
export API_GATEWAY_STAGE=prod
export API_GATEWAY_URL=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod

# RDS Configuration
export RDS_ENDPOINT=learntrac-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com
export RDS_PORT=5432
export RDS_DATABASE=learntrac
export RDS_USERNAME=learntrac_admin
export RDS_PASSWORD=your-secure-password

# ElastiCache Configuration
export REDIS_ENDPOINT=learntrac-redis.xxxxxx.cache.amazonaws.com
export REDIS_PORT=6379
export REDIS_AUTH_TOKEN=optional-auth-token

# VPC Configuration
export VPC_ID=vpc-xxxxxxxxxxxxxxxxx
export PRIVATE_SUBNET_IDS=subnet-xxxxx,subnet-yyyyy
export PUBLIC_SUBNET_IDS=subnet-aaaaa,subnet-bbbbb
```

### Configuration File

Edit `docs/testing/infra_tests/config.sh` to set default values or load from `.env.test`.

## Usage

### Running All Tests

```bash
# Make scripts executable
chmod +x docs/testing/infra_tests/*.sh
chmod +x docs/testing/infra_tests/suites/*.sh

# Run all tests sequentially
./docs/testing/infra_tests/run_all_infra_tests.sh

# Run all tests in parallel (faster)
./docs/testing/infra_tests/run_all_infra_tests.sh --parallel

# Specify custom output directory
./docs/testing/infra_tests/run_all_infra_tests.sh --output ./test-results
```

### Running Individual Test Suites

```bash
# Run specific test suite
./docs/testing/infra_tests/run_all_infra_tests.sh --suite terraform

# Or run directly
./docs/testing/infra_tests/suites/test_cognito.sh
```

### Test Options

- `--parallel, -p` - Run tests in parallel (requires GNU parallel or uses background jobs)
- `--output DIR, -o DIR` - Specify output directory for results
- `--suite NAME, -s NAME` - Run only a specific test suite
- `--help, -h` - Show usage information

## Test Suites Detail

### 1. Terraform Tests (`test_terraform.sh`)

Validates:
- Required .tf files exist (main.tf, variables.tf, outputs.tf, versions.tf)
- Terraform configuration is valid (`terraform validate`)
- S3 backend is configured with versioning
- DynamoDB lock table exists
- Resource declarations for key AWS services
- State consistency (no drift)

### 2. Cognito Tests (`test_cognito.sh`)

Validates:
- User pool exists and is active
- App client is configured
- OAuth flows are enabled
- Password policy meets requirements
- MFA configuration
- JWT token settings
- Callback URLs match API Gateway

### 3. API Gateway Tests (`test_apigw.sh`)

Validates:
- REST API exists
- Cognito authorizer is configured
- Resources and methods are defined
- Authorization is applied to methods
- CORS is configured
- Deployment stage exists
- Endpoint is accessible
- Throttling is configured

### 4. RDS Tests (`test_rds.sh`)

Validates:
- RDS instance exists and is available
- PostgreSQL version is 15.x
- Database connectivity
- Security configuration (encryption, backups)
- Trac database exists
- All Trac schema tables are present
- Admin user is configured

### 5. Redis Tests (`test_redis.sh`)

Validates:
- ElastiCache cluster exists and is available
- Redis connectivity
- Cluster mode and failover settings
- Parameter group configuration
- Security group rules
- Subnet group for Multi-AZ
- Backup configuration
- Basic Redis operations (SET/GET)

### 6. Learning Schema Tests (`test_learning_schema.sh`)

Validates:
- Learning schema exists
- UUID extension is enabled
- All learning tables exist
- Table structures are correct
- Foreign keys to Trac tables
- User permissions
- Indexes are configured

### 7. Network Tests (`test_network.sh`)

Validates:
- VPC exists with DNS enabled
- Subnets span multiple AZs
- Internet gateway is attached
- NAT gateway for private subnets
- Security group baseline
- Application-specific security groups
- Network ACLs
- VPC flow logs (optional)

### 8. Documentation Tests (`test_docs.sh`)

Validates:
- README.md exists with key sections
- Terraform outputs are documented
- Variables have descriptions
- Example tfvars file exists
- Architecture diagram
- Runbook/operations guide
- Security documentation

## Output and Results

### Test Results Location

Results are stored in timestamped files:

```
docs/testing/infra_tests/test-results/
├── infrastructure_tests_20240115_143022.log    # Master log
├── test_summary_20240115_143022.txt           # Summary report
├── test_terraform_20240115_143022.log         # Individual suite logs
├── test_cognito_20240115_143022.log
├── test_apigw_20240115_143022.log
├── test_rds_20240115_143022.log
├── test_redis_20240115_143022.log
├── test_learning_schema_20240115_143022.log
├── test_network_20240115_143022.log
└── test_docs_20240115_143022.log
```

### Understanding Results

Each test outputs:
- `[PASS]` - Test succeeded
- `[FAIL]` - Test failed (review logs)
- `[SKIP]` - Test skipped (missing configuration)
- `[WARN]` - Warning but not a failure

### Summary Report

The summary report includes:
- Total tests run per suite
- Pass/fail/skip counts
- Recommendations for failures
- Links to detailed logs

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Infrastructure Tests

on:
  push:
    paths:
      - 'learntrac-infrastructure/**'
      - 'docs/testing/infra_tests/**'

jobs:
  infra-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq postgresql-client redis-tools
          
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        
      - name: Run infrastructure tests
        env:
          RDS_PASSWORD: ${{ secrets.RDS_PASSWORD }}
          REDIS_AUTH_TOKEN: ${{ secrets.REDIS_AUTH_TOKEN }}
        run: |
          chmod +x docs/testing/infra_tests/*.sh
          chmod +x docs/testing/infra_tests/suites/*.sh
          ./docs/testing/infra_tests/run_all_infra_tests.sh --parallel
          
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: infrastructure-test-results
          path: docs/testing/infra_tests/test-results/
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Ensure AWS CLI is configured: `aws configure`
   - Check IAM permissions for all required services

2. **Connection Timeouts**
   - Verify security group rules allow access
   - Check if running from allowed network/VPN
   - Ensure resources are in expected region

3. **Missing Dependencies**
   - Install jq: `brew install jq` (macOS) or `apt-get install jq` (Linux)
   - Install PostgreSQL client: `brew install postgresql` or `apt-get install postgresql-client`
   - Install Redis client: `brew install redis` or `apt-get install redis-tools`

4. **Configuration Not Found**
   - Verify environment variables are set
   - Check `.env.test` file exists and is sourced
   - Ensure resource IDs/names are correct

### Debug Mode

Enable verbose output by editing test scripts:

```bash
# Add to individual test scripts
set -x  # Enable debug output
```

## Extending the Test Suite

### Adding New Tests

1. Create new test function in appropriate suite:

```bash
test_new_feature() {
    # Test implementation
    if [ condition ]; then
        log_success "New feature test passed"
        return 0
    else
        log_error "New feature test failed"
        return 1
    fi
}
```

2. Add to test execution:

```bash
run_test "New feature description" test_new_feature
```

### Creating New Test Suites

1. Create `docs/testing/infra_tests/suites/test_newsuite.sh`
2. Follow the existing pattern with sourcing config and utilities
3. Add to `TEST_SUITES` and `TEST_ORDER` in `run_all_infra_tests.sh`

## Best Practices

1. **Run tests regularly** - After any infrastructure changes
2. **Keep configuration updated** - Reflect actual resource IDs
3. **Review warnings** - They may indicate future issues
4. **Store results** - Keep test history for compliance
5. **Automate in CI/CD** - Catch issues before production

## Support

For issues or questions:
1. Check individual test logs for detailed error messages
2. Verify configuration matches actual AWS resources
3. Ensure all prerequisites are installed
4. Review AWS service quotas and limits

---

This test suite ensures the AWS infrastructure is properly configured and ready for the LearnTrac application deployment.