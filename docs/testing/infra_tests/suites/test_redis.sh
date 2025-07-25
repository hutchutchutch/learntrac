#!/bin/bash
# Test Suite: ElastiCache Redis Validation
# Validates subtask 1.5 (ElastiCache configuration)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_redis_cluster_exists() {
    if [ -z "$REDIS_ENDPOINT" ]; then
        log_error "REDIS_ENDPOINT not set"
        return 1
    fi
    
    # Extract cluster ID from endpoint
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    local cluster_info=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --show-cache-node-info \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$cluster_info" ]; then
        local status=$(echo "$cluster_info" | jq -r '.CacheClusters[0].CacheClusterStatus')
        local engine=$(echo "$cluster_info" | jq -r '.CacheClusters[0].Engine')
        local engine_version=$(echo "$cluster_info" | jq -r '.CacheClusters[0].EngineVersion')
        local node_type=$(echo "$cluster_info" | jq -r '.CacheClusters[0].CacheNodeType')
        
        log_info "Redis Cluster: $cluster_id"
        log_info "  Status: $status"
        log_info "  Engine: $engine $engine_version"
        log_info "  Node Type: $node_type"
        
        if [ "$status" = "available" ]; then
            log_success "Redis cluster is available"
            return 0
        else
            log_error "Redis cluster is not available (status: $status)"
            return 1
        fi
    else
        log_error "Redis cluster not found: $cluster_id"
        return 1
    fi
}

test_redis_connectivity() {
    log_info "Testing Redis connectivity to $REDIS_ENDPOINT:$REDIS_PORT"
    
    # First test TCP connectivity
    if test_tcp_connectivity "$REDIS_ENDPOINT" "$REDIS_PORT" 5; then
        log_success "TCP connection to Redis successful"
        
        # Check if redis-cli is available
        if ! command -v redis-cli &> /dev/null; then
            log_warning "redis-cli not installed, skipping Redis protocol test"
            return 0
        fi
        
        # Test Redis connection
        local pong=$(test_redis_connection "$REDIS_ENDPOINT" "$REDIS_PORT" "$REDIS_AUTH_TOKEN")
        
        if [ "$pong" = "PONG" ]; then
            log_success "Redis connection successful (PING/PONG verified)"
            return 0
        else
            log_error "Redis connection failed (no PONG response)"
            return 1
        fi
    else
        log_error "TCP connection to Redis failed"
        return 1
    fi
}

test_redis_cluster_mode() {
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    local cluster_info=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$cluster_info" ]; then
        local num_nodes=$(echo "$cluster_info" | jq -r '.CacheClusters[0].NumCacheNodes')
        
        log_info "Cache nodes: $num_nodes"
        
        # Check if it's a replication group (cluster mode)
        local replication_group_id=$(echo "$cluster_info" | jq -r '.CacheClusters[0].ReplicationGroupId // empty')
        
        if [ -n "$replication_group_id" ]; then
            log_info "Part of replication group: $replication_group_id"
            
            # Get replication group details
            local rep_group_info=$(aws elasticache describe-replication-groups \
                --replication-group-id "$replication_group_id" \
                --region "$AWS_REGION" 2>/dev/null)
            
            if [ -n "$rep_group_info" ]; then
                local cluster_enabled=$(echo "$rep_group_info" | jq -r '.ReplicationGroups[0].ClusterEnabled')
                local automatic_failover=$(echo "$rep_group_info" | jq -r '.ReplicationGroups[0].AutomaticFailover')
                local multi_az=$(echo "$rep_group_info" | jq -r '.ReplicationGroups[0].MultiAZ')
                
                log_info "  Cluster Mode: $cluster_enabled"
                log_info "  Automatic Failover: $automatic_failover"
                log_info "  Multi-AZ: $multi_az"
                
                if [ "$automatic_failover" = "enabled" ]; then
                    log_success "Automatic failover is enabled"
                else
                    log_warning "Automatic failover is not enabled"
                fi
                
                return 0
            fi
        else
            log_info "Standalone cache cluster (no replication group)"
        fi
        
        return 0
    else
        log_error "Failed to retrieve cluster mode information"
        return 1
    fi
}

test_redis_parameter_group() {
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    local param_group=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --region "$AWS_REGION" \
        --query 'CacheClusters[0].CacheParameterGroup.CacheParameterGroupName' \
        --output text 2>/dev/null)
    
    if [ -n "$param_group" ] && [ "$param_group" != "None" ]; then
        log_info "Parameter group: $param_group"
        
        # Get parameter details
        local params=$(aws elasticache describe-cache-parameters \
            --cache-parameter-group-name "$param_group" \
            --region "$AWS_REGION" 2>/dev/null)
        
        if [ -n "$params" ]; then
            # Check important parameters
            local maxmemory_policy=$(echo "$params" | jq -r '.Parameters[] | select(.ParameterName == "maxmemory-policy") | .ParameterValue')
            local timeout=$(echo "$params" | jq -r '.Parameters[] | select(.ParameterName == "timeout") | .ParameterValue')
            
            log_info "Key parameters:"
            [ -n "$maxmemory_policy" ] && log_info "  maxmemory-policy: $maxmemory_policy"
            [ -n "$timeout" ] && log_info "  timeout: $timeout seconds"
            
            log_success "Parameter group is configured"
            return 0
        else
            log_warning "Could not retrieve parameter details"
            return 0
        fi
    else
        log_warning "Using default parameter group"
        return 0
    fi
}

test_redis_security_group() {
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    local security_groups=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --region "$AWS_REGION" \
        --query 'CacheClusters[0].SecurityGroups[].SecurityGroupId' \
        --output text 2>/dev/null)
    
    if [ -n "$security_groups" ]; then
        log_info "Security groups:"
        for sg in $security_groups; do
            log_info "  - $sg"
            
            # Check inbound rules for Redis port
            local redis_rules=$(aws ec2 describe-security-groups \
                --group-ids "$sg" \
                --region "$AWS_REGION" \
                --query "SecurityGroups[0].IpPermissions[?FromPort==\`$REDIS_PORT\`]" 2>/dev/null)
            
            if [ "$redis_rules" != "[]" ] && [ -n "$redis_rules" ]; then
                log_success "Security group $sg has Redis port ($REDIS_PORT) rules"
            else
                log_warning "Security group $sg may not have Redis port rules"
            fi
        done
        
        return 0
    else
        log_error "No security groups found for Redis cluster"
        return 1
    fi
}

test_redis_subnet_group() {
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    local subnet_group=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --region "$AWS_REGION" \
        --query 'CacheClusters[0].CacheSubnetGroupName' \
        --output text 2>/dev/null)
    
    if [ -n "$subnet_group" ] && [ "$subnet_group" != "None" ]; then
        log_info "Subnet group: $subnet_group"
        
        # Get subnet details
        local subnet_info=$(aws elasticache describe-cache-subnet-groups \
            --cache-subnet-group-name "$subnet_group" \
            --region "$AWS_REGION" 2>/dev/null)
        
        if [ -n "$subnet_info" ]; then
            local subnet_count=$(echo "$subnet_info" | jq -r '.CacheSubnetGroups[0].Subnets | length')
            log_info "Number of subnets: $subnet_count"
            
            # List availability zones
            local azs=$(echo "$subnet_info" | jq -r '.CacheSubnetGroups[0].Subnets[].SubnetAvailabilityZone.Name' | sort -u)
            log_info "Availability zones:"
            echo "$azs" | while read -r az; do
                log_info "  - $az"
            done
            
            if [ "$subnet_count" -ge 2 ]; then
                log_success "Multi-AZ subnet configuration verified"
                return 0
            else
                log_warning "Only $subnet_count subnet(s) configured"
                return 0
            fi
        fi
    else
        log_error "No subnet group found for Redis cluster"
        return 1
    fi
}

test_redis_backup_configuration() {
    local cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
    
    # Check if cluster has snapshot configuration
    local snapshot_retention=$(aws elasticache describe-cache-clusters \
        --cache-cluster-id "$cluster_id" \
        --region "$AWS_REGION" \
        --query 'CacheClusters[0].SnapshotRetentionLimit' \
        --output text 2>/dev/null)
    
    if [ -n "$snapshot_retention" ] && [ "$snapshot_retention" != "None" ]; then
        if [ "$snapshot_retention" -gt 0 ]; then
            log_success "Automated backups enabled (retention: $snapshot_retention days)"
            
            # Check snapshot window
            local snapshot_window=$(aws elasticache describe-cache-clusters \
                --cache-cluster-id "$cluster_id" \
                --region "$AWS_REGION" \
                --query 'CacheClusters[0].SnapshotWindow' \
                --output text 2>/dev/null)
            
            [ -n "$snapshot_window" ] && [ "$snapshot_window" != "None" ] && \
                log_info "Snapshot window: $snapshot_window"
            
            return 0
        else
            log_warning "Automated backups not enabled"
            return 0
        fi
    else
        # Check replication group level backup settings
        local replication_group_id=$(aws elasticache describe-cache-clusters \
            --cache-cluster-id "$cluster_id" \
            --region "$AWS_REGION" \
            --query 'CacheClusters[0].ReplicationGroupId' \
            --output text 2>/dev/null)
        
        if [ -n "$replication_group_id" ] && [ "$replication_group_id" != "None" ]; then
            local rg_retention=$(aws elasticache describe-replication-groups \
                --replication-group-id "$replication_group_id" \
                --region "$AWS_REGION" \
                --query 'ReplicationGroups[0].SnapshotRetentionLimit' \
                --output text 2>/dev/null)
            
            if [ -n "$rg_retention" ] && [ "$rg_retention" -gt 0 ]; then
                log_success "Automated backups enabled at replication group level (retention: $rg_retention days)"
                return 0
            fi
        fi
        
        log_warning "Backup configuration not found"
        return 0
    fi
}

test_redis_basic_operations() {
    if ! command -v redis-cli &> /dev/null; then
        skip_test "Redis basic operations" "redis-cli not installed"
        return 0
    fi
    
    log_info "Testing basic Redis operations..."
    
    # Test SET operation
    local test_key="test:infrastructure:$(date +%s)"
    local test_value="infrastructure_test_value"
    
    local set_result
    if [ -n "$REDIS_AUTH_TOKEN" ]; then
        set_result=$(redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" -a "$REDIS_AUTH_TOKEN" --no-auth-warning SET "$test_key" "$test_value" EX 60 2>/dev/null)
    else
        set_result=$(redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" SET "$test_key" "$test_value" EX 60 2>/dev/null)
    fi
    
    if [ "$set_result" = "OK" ]; then
        log_success "Redis SET operation successful"
        
        # Test GET operation
        local get_result
        if [ -n "$REDIS_AUTH_TOKEN" ]; then
            get_result=$(redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" -a "$REDIS_AUTH_TOKEN" --no-auth-warning GET "$test_key" 2>/dev/null)
        else
            get_result=$(redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" GET "$test_key" 2>/dev/null)
        fi
        
        if [ "$get_result" = "$test_value" ]; then
            log_success "Redis GET operation successful"
            
            # Clean up
            if [ -n "$REDIS_AUTH_TOKEN" ]; then
                redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" -a "$REDIS_AUTH_TOKEN" --no-auth-warning DEL "$test_key" >/dev/null 2>&1
            else
                redis-cli -h "$REDIS_ENDPOINT" -p "$REDIS_PORT" DEL "$test_key" >/dev/null 2>&1
            fi
            
            return 0
        else
            log_error "Redis GET operation failed"
            return 1
        fi
    else
        log_error "Redis SET operation failed"
        return 1
    fi
}

# Main test execution
main() {
    log_info "Starting ElastiCache Redis Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Run tests
    run_test "Redis cluster exists" test_redis_cluster_exists
    run_test "Redis connectivity" test_redis_connectivity
    run_test "Redis cluster mode" test_redis_cluster_mode
    run_test "Redis parameter group" test_redis_parameter_group
    run_test "Redis security group" test_redis_security_group
    run_test "Redis subnet group" test_redis_subnet_group
    run_test "Redis backup configuration" test_redis_backup_configuration
    run_test "Redis basic operations" test_redis_basic_operations
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"