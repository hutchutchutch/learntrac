#!/bin/bash
# Test Suite: RDS PostgreSQL Configuration
# Validates subtasks 1.4 (RDS config) and 1.6 (Trac schema)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_rds_instance_exists() {
    if [ -z "$RDS_ENDPOINT" ]; then
        log_error "RDS_ENDPOINT not set"
        return 1
    fi
    
    # Extract instance identifier from endpoint
    local instance_id=$(echo "$RDS_ENDPOINT" | cut -d'.' -f1)
    
    local instance_info=$(aws rds describe-db-instances \
        --db-instance-identifier "$instance_id" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$instance_info" ]; then
        local status=$(echo "$instance_info" | jq -r '.DBInstances[0].DBInstanceStatus')
        local engine=$(echo "$instance_info" | jq -r '.DBInstances[0].Engine')
        local engine_version=$(echo "$instance_info" | jq -r '.DBInstances[0].EngineVersion')
        
        log_info "RDS Instance: $instance_id"
        log_info "  Status: $status"
        log_info "  Engine: $engine $engine_version"
        
        if [ "$status" = "available" ]; then
            log_success "RDS instance is available"
            return 0
        else
            log_error "RDS instance is not available (status: $status)"
            return 1
        fi
    else
        log_error "RDS instance not found: $instance_id"
        return 1
    fi
}

test_rds_postgresql_version() {
    local instance_id=$(echo "$RDS_ENDPOINT" | cut -d'.' -f1)
    
    local engine_version=$(aws rds describe-db-instances \
        --db-instance-identifier "$instance_id" \
        --region "$AWS_REGION" \
        --query 'DBInstances[0].EngineVersion' \
        --output text 2>/dev/null)
    
    if [ -n "$engine_version" ]; then
        local major_version=$(echo "$engine_version" | cut -d'.' -f1)
        
        if [ "$major_version" = "15" ]; then
            log_success "PostgreSQL version is 15.x ($engine_version)"
            return 0
        else
            log_error "PostgreSQL version is not 15.x (found: $engine_version)"
            return 1
        fi
    else
        log_error "Failed to retrieve PostgreSQL version"
        return 1
    fi
}

test_rds_connectivity() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "RDS connectivity" "RDS_PASSWORD not set"
        return 0
    fi
    
    log_info "Testing RDS connectivity to $RDS_ENDPOINT:$RDS_PORT"
    
    # First test TCP connectivity
    if test_tcp_connectivity "$RDS_ENDPOINT" "$RDS_PORT" 5; then
        log_success "TCP connection to RDS successful"
        
        # Then test PostgreSQL connection
        local pg_version=$(test_postgres_connection \
            "$RDS_ENDPOINT" \
            "$RDS_PORT" \
            "$RDS_DATABASE" \
            "$RDS_USERNAME" \
            "$RDS_PASSWORD")
        
        if [ -n "$pg_version" ]; then
            log_success "PostgreSQL connection successful"
            log_info "Server version: $pg_version"
            return 0
        else
            log_error "PostgreSQL connection failed"
            return 1
        fi
    else
        log_error "TCP connection to RDS failed"
        return 1
    fi
}

test_rds_security_configuration() {
    local instance_id=$(echo "$RDS_ENDPOINT" | cut -d'.' -f1)
    
    local instance_info=$(aws rds describe-db-instances \
        --db-instance-identifier "$instance_id" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$instance_info" ]; then
        # Check encryption
        local encrypted=$(echo "$instance_info" | jq -r '.DBInstances[0].StorageEncrypted')
        if [ "$encrypted" = "true" ]; then
            log_success "RDS storage encryption is enabled"
        else
            log_warning "RDS storage encryption is not enabled"
        fi
        
        # Check backup retention
        local backup_retention=$(echo "$instance_info" | jq -r '.DBInstances[0].BackupRetentionPeriod')
        if [ "$backup_retention" -gt 0 ]; then
            log_success "Automated backups enabled (retention: $backup_retention days)"
        else
            log_error "Automated backups not enabled"
            return 1
        fi
        
        # Check Multi-AZ
        local multi_az=$(echo "$instance_info" | jq -r '.DBInstances[0].MultiAZ')
        if [ "$multi_az" = "true" ]; then
            log_success "Multi-AZ deployment is enabled"
        else
            log_warning "Multi-AZ deployment is not enabled"
        fi
        
        # Check security groups
        local security_groups=$(echo "$instance_info" | jq -r '.DBInstances[0].VpcSecurityGroups[].VpcSecurityGroupId')
        log_info "Security groups:"
        echo "$security_groups" | while read -r sg; do
            log_info "  - $sg"
        done
        
        return 0
    else
        log_error "Failed to retrieve RDS security configuration"
        return 1
    fi
}

test_trac_database_exists() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "Trac database existence" "RDS_PASSWORD not set"
        return 0
    fi
    
    local db_exists=$(PGPASSWORD="$RDS_PASSWORD" psql \
        -h "$RDS_ENDPOINT" \
        -p "$RDS_PORT" \
        -U "$RDS_USERNAME" \
        -d postgres \
        -t -A \
        -c "SELECT 1 FROM pg_database WHERE datname='$RDS_DATABASE';" 2>/dev/null)
    
    if [ "$db_exists" = "1" ]; then
        log_success "Database '$RDS_DATABASE' exists"
        return 0
    else
        log_error "Database '$RDS_DATABASE' does not exist"
        return 1
    fi
}

test_trac_schema_tables() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "Trac schema tables" "RDS_PASSWORD not set"
        return 0
    fi
    
    log_info "Checking Trac schema tables..."
    
    local missing_tables=0
    for table in $TRAC_SCHEMA_TABLES; do
        if check_postgres_table_exists \
            "$RDS_ENDPOINT" \
            "$RDS_DATABASE" \
            "public" \
            "$table" \
            "$RDS_USERNAME" \
            "$RDS_PASSWORD"; then
            log_success "Found Trac table: $table"
        else
            log_error "Missing Trac table: $table"
            missing_tables=$((missing_tables + 1))
        fi
    done
    
    if [ "$missing_tables" -eq 0 ]; then
        log_success "All Trac tables are present"
        return 0
    else
        log_error "$missing_tables Trac tables are missing"
        return 1
    fi
}

test_trac_admin_user() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "Trac admin user" "RDS_PASSWORD not set"
        return 0
    fi
    
    # Check if admin permissions exist
    local admin_perms=$(PGPASSWORD="$RDS_PASSWORD" psql \
        -h "$RDS_ENDPOINT" \
        -p "$RDS_PORT" \
        -U "$RDS_USERNAME" \
        -d "$RDS_DATABASE" \
        -t -A \
        -c "SELECT COUNT(*) FROM permission WHERE username='admin' AND action='TRAC_ADMIN';" 2>/dev/null)
    
    if [ "$admin_perms" -gt 0 ]; then
        log_success "Trac admin user is configured"
        return 0
    else
        log_warning "Trac admin user not found or not configured"
        return 0  # Warning, not failure
    fi
}

test_trac_table_relationships() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "Trac table relationships" "RDS_PASSWORD not set"
        return 0
    fi
    
    # Check foreign key constraints
    local fk_count=$(PGPASSWORD="$RDS_PASSWORD" psql \
        -h "$RDS_ENDPOINT" \
        -p "$RDS_PORT" \
        -U "$RDS_USERNAME" \
        -d "$RDS_DATABASE" \
        -t -A \
        -c "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema='public';" 2>/dev/null)
    
    if [ -n "$fk_count" ] && [ "$fk_count" -gt 0 ]; then
        log_info "Found $fk_count foreign key constraints"
        log_success "Table relationships are configured"
        return 0
    else
        log_warning "No foreign key constraints found (may be normal for Trac)"
        return 0
    fi
}

test_database_extensions() {
    if [ -z "$RDS_PASSWORD" ]; then
        skip_test "Database extensions" "RDS_PASSWORD not set"
        return 0
    fi
    
    # Check for UUID extension (needed for learning schema)
    local uuid_ext=$(PGPASSWORD="$RDS_PASSWORD" psql \
        -h "$RDS_ENDPOINT" \
        -p "$RDS_PORT" \
        -U "$RDS_USERNAME" \
        -d "$RDS_DATABASE" \
        -t -A \
        -c "SELECT 1 FROM pg_extension WHERE extname='uuid-ossp';" 2>/dev/null)
    
    if [ "$uuid_ext" = "1" ]; then
        log_success "UUID extension is installed"
        return 0
    else
        log_warning "UUID extension not installed (needed for learning schema)"
        return 0  # Warning for now, will be error in learning schema test
    fi
}

# Main test execution
main() {
    log_info "Starting RDS PostgreSQL Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Run tests
    run_test "RDS instance exists" test_rds_instance_exists
    run_test "RDS PostgreSQL version 15" test_rds_postgresql_version
    run_test "RDS connectivity" test_rds_connectivity
    run_test "RDS security configuration" test_rds_security_configuration
    run_test "Trac database exists" test_trac_database_exists
    run_test "Trac schema tables" test_trac_schema_tables
    run_test "Trac admin user" test_trac_admin_user
    run_test "Trac table relationships" test_trac_table_relationships
    run_test "Database extensions" test_database_extensions
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"