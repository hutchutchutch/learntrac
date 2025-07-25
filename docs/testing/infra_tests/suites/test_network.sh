#!/bin/bash
# Test Suite: VPC and Network Security Validation
# Validates subtask 1.8 (VPC and security groups)

set -euo pipefail

# Source configuration and utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"
source "$SCRIPT_DIR/../utils/common.sh"

# Test Functions

test_vpc_exists() {
    if [ -z "$VPC_ID" ]; then
        log_error "VPC_ID not set"
        return 1
    fi
    
    local vpc_info=$(aws ec2 describe-vpcs \
        --vpc-ids "$VPC_ID" \
        --region "$AWS_REGION" 2>/dev/null)
    
    if [ -n "$vpc_info" ]; then
        local state=$(echo "$vpc_info" | jq -r '.Vpcs[0].State')
        local cidr=$(echo "$vpc_info" | jq -r '.Vpcs[0].CidrBlock')
        local dns_support=$(echo "$vpc_info" | jq -r '.Vpcs[0].EnableDnsSupport')
        local dns_hostnames=$(echo "$vpc_info" | jq -r '.Vpcs[0].EnableDnsHostnames')
        
        log_info "VPC: $VPC_ID"
        log_info "  State: $state"
        log_info "  CIDR: $cidr"
        log_info "  DNS Support: $dns_support"
        log_info "  DNS Hostnames: $dns_hostnames"
        
        if [ "$state" = "available" ]; then
            log_success "VPC is available"
            
            # Check DNS settings
            if [ "$dns_support" = "true" ] && [ "$dns_hostnames" = "true" ]; then
                log_success "DNS is properly configured"
            else
                log_warning "DNS settings may need adjustment"
            fi
            
            return 0
        else
            log_error "VPC is not available (state: $state)"
            return 1
        fi
    else
        log_error "VPC not found: $VPC_ID"
        return 1
    fi
}

test_subnets_configuration() {
    # Test private subnets
    if [ -n "$PRIVATE_SUBNET_IDS" ]; then
        log_info "Checking private subnets..."
        
        local private_azs=""
        for subnet_id in $(echo "$PRIVATE_SUBNET_IDS" | tr ',' ' '); do
            local subnet_info=$(aws ec2 describe-subnets \
                --subnet-ids "$subnet_id" \
                --region "$AWS_REGION" 2>/dev/null)
            
            if [ -n "$subnet_info" ]; then
                local az=$(echo "$subnet_info" | jq -r '.Subnets[0].AvailabilityZone')
                local cidr=$(echo "$subnet_info" | jq -r '.Subnets[0].CidrBlock')
                local available_ips=$(echo "$subnet_info" | jq -r '.Subnets[0].AvailableIpAddressCount')
                
                log_info "  Private subnet $subnet_id:"
                log_info "    AZ: $az"
                log_info "    CIDR: $cidr"
                log_info "    Available IPs: $available_ips"
                
                private_azs="$private_azs $az"
            else
                log_error "Private subnet not found: $subnet_id"
                return 1
            fi
        done
        
        # Check multi-AZ
        local unique_private_azs=$(echo "$private_azs" | tr ' ' '\n' | sort -u | wc -l)
        if [ "$unique_private_azs" -ge 2 ]; then
            log_success "Private subnets span $unique_private_azs availability zones"
        else
            log_warning "Private subnets only in $unique_private_azs availability zone(s)"
        fi
    else
        log_warning "PRIVATE_SUBNET_IDS not configured"
    fi
    
    # Test public subnets
    if [ -n "$PUBLIC_SUBNET_IDS" ]; then
        log_info "Checking public subnets..."
        
        local public_azs=""
        for subnet_id in $(echo "$PUBLIC_SUBNET_IDS" | tr ',' ' '); do
            local subnet_info=$(aws ec2 describe-subnets \
                --subnet-ids "$subnet_id" \
                --region "$AWS_REGION" 2>/dev/null)
            
            if [ -n "$subnet_info" ]; then
                local az=$(echo "$subnet_info" | jq -r '.Subnets[0].AvailabilityZone')
                local cidr=$(echo "$subnet_info" | jq -r '.Subnets[0].CidrBlock')
                local auto_public_ip=$(echo "$subnet_info" | jq -r '.Subnets[0].MapPublicIpOnLaunch')
                
                log_info "  Public subnet $subnet_id:"
                log_info "    AZ: $az"
                log_info "    CIDR: $cidr"
                log_info "    Auto-assign public IP: $auto_public_ip"
                
                public_azs="$public_azs $az"
            else
                log_error "Public subnet not found: $subnet_id"
                return 1
            fi
        done
        
        # Check multi-AZ
        local unique_public_azs=$(echo "$public_azs" | tr ' ' '\n' | sort -u | wc -l)
        if [ "$unique_public_azs" -ge 2 ]; then
            log_success "Public subnets span $unique_public_azs availability zones"
        else
            log_warning "Public subnets only in $unique_public_azs availability zone(s)"
        fi
    else
        log_warning "PUBLIC_SUBNET_IDS not configured"
    fi
    
    return 0
}

test_internet_gateway() {
    # Find internet gateway attached to VPC
    local igw=$(aws ec2 describe-internet-gateways \
        --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'InternetGateways[0].InternetGatewayId' \
        --output text 2>/dev/null)
    
    if [ -n "$igw" ] && [ "$igw" != "None" ]; then
        log_success "Internet gateway found: $igw"
        
        # Check route tables for public subnets
        if [ -n "$PUBLIC_SUBNET_IDS" ]; then
            for subnet_id in $(echo "$PUBLIC_SUBNET_IDS" | tr ',' ' '); do
                local route_table=$(aws ec2 describe-route-tables \
                    --filters "Name=association.subnet-id,Values=$subnet_id" \
                    --region "$AWS_REGION" \
                    --query 'RouteTables[0].RouteTableId' \
                    --output text 2>/dev/null)
                
                if [ -n "$route_table" ] && [ "$route_table" != "None" ]; then
                    # Check for default route to IGW
                    local igw_route=$(aws ec2 describe-route-tables \
                        --route-table-ids "$route_table" \
                        --region "$AWS_REGION" \
                        --query "RouteTables[0].Routes[?GatewayId=='$igw' && DestinationCidrBlock=='0.0.0.0/0']" 2>/dev/null)
                    
                    if [ "$igw_route" != "[]" ] && [ -n "$igw_route" ]; then
                        log_success "Public subnet $subnet_id has route to internet gateway"
                    else
                        log_error "Public subnet $subnet_id missing route to internet gateway"
                        return 1
                    fi
                fi
            done
        fi
        
        return 0
    else
        log_error "No internet gateway found for VPC"
        return 1
    fi
}

test_nat_gateway() {
    # Find NAT gateways in VPC
    local nat_gateways=$(aws ec2 describe-nat-gateways \
        --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
        --region "$AWS_REGION" \
        --query 'NatGateways[].NatGatewayId' \
        --output text 2>/dev/null)
    
    if [ -n "$nat_gateways" ] && [ "$nat_gateways" != "None" ]; then
        local nat_count=$(echo "$nat_gateways" | wc -w)
        log_info "Found $nat_count NAT gateway(s)"
        
        for nat_id in $nat_gateways; do
            local nat_info=$(aws ec2 describe-nat-gateways \
                --nat-gateway-ids "$nat_id" \
                --region "$AWS_REGION" 2>/dev/null)
            
            local subnet_id=$(echo "$nat_info" | jq -r '.NatGateways[0].SubnetId')
            local public_ip=$(echo "$nat_info" | jq -r '.NatGateways[0].NatGatewayAddresses[0].PublicIp')
            
            log_info "  NAT Gateway $nat_id:"
            log_info "    Subnet: $subnet_id"
            log_info "    Public IP: $public_ip"
        done
        
        # Check route tables for private subnets
        if [ -n "$PRIVATE_SUBNET_IDS" ]; then
            for subnet_id in $(echo "$PRIVATE_SUBNET_IDS" | tr ',' ' '); do
                local route_table=$(aws ec2 describe-route-tables \
                    --filters "Name=association.subnet-id,Values=$subnet_id" \
                    --region "$AWS_REGION" \
                    --query 'RouteTables[0].RouteTableId' \
                    --output text 2>/dev/null)
                
                if [ -n "$route_table" ] && [ "$route_table" != "None" ]; then
                    # Check for default route to NAT
                    local nat_route=$(aws ec2 describe-route-tables \
                        --route-table-ids "$route_table" \
                        --region "$AWS_REGION" \
                        --query "RouteTables[0].Routes[?NatGatewayId!=null && DestinationCidrBlock=='0.0.0.0/0']" 2>/dev/null)
                    
                    if [ "$nat_route" != "[]" ] && [ -n "$nat_route" ]; then
                        log_success "Private subnet $subnet_id has route to NAT gateway"
                    else
                        log_warning "Private subnet $subnet_id may not have route to NAT gateway"
                    fi
                fi
            done
        fi
        
        log_success "NAT gateway configuration verified"
        return 0
    else
        log_warning "No NAT gateways found (may be using NAT instances)"
        return 0
    fi
}

test_security_groups_baseline() {
    # Get all security groups in VPC
    local security_groups=$(aws ec2 describe-security-groups \
        --filters "Name=vpc-id,Values=$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'SecurityGroups[].GroupId' \
        --output text 2>/dev/null)
    
    if [ -n "$security_groups" ]; then
        local sg_count=$(echo "$security_groups" | wc -w)
        log_info "Found $sg_count security group(s) in VPC"
        
        # Check for overly permissive rules
        local issues=0
        
        for sg_id in $security_groups; do
            local sg_info=$(aws ec2 describe-security-groups \
                --group-ids "$sg_id" \
                --region "$AWS_REGION" 2>/dev/null)
            
            local sg_name=$(echo "$sg_info" | jq -r '.SecurityGroups[0].GroupName')
            
            # Check for 0.0.0.0/0 ingress rules
            local open_ingress=$(echo "$sg_info" | jq -r '.SecurityGroups[0].IpPermissions[] | select(.IpRanges[]?.CidrIp == "0.0.0.0/0" or .Ipv6Ranges[]?.CidrIpv6 == "::/0")')
            
            if [ -n "$open_ingress" ]; then
                log_warning "Security group $sg_name ($sg_id) has rules open to internet"
                
                # Check which ports are open
                local open_ports=$(echo "$open_ingress" | jq -r 'select(.FromPort != null) | "\(.FromPort)-\(.ToPort)"' | sort -u)
                for port_range in $open_ports; do
                    log_warning "  Open to internet: Port $port_range"
                done
                
                issues=$((issues + 1))
            fi
        done
        
        if [ "$issues" -eq 0 ]; then
            log_success "No overly permissive security group rules found"
        else
            log_warning "Found $issues security group(s) with potentially risky rules"
        fi
        
        return 0
    else
        log_error "No security groups found in VPC"
        return 1
    fi
}

test_application_security_groups() {
    log_info "Checking application-specific security groups..."
    
    # RDS security group
    if [ -n "$RDS_ENDPOINT" ]; then
        local rds_instance_id=$(echo "$RDS_ENDPOINT" | cut -d'.' -f1)
        local rds_sgs=$(aws rds describe-db-instances \
            --db-instance-identifier "$rds_instance_id" \
            --region "$AWS_REGION" \
            --query 'DBInstances[0].VpcSecurityGroups[].VpcSecurityGroupId' \
            --output text 2>/dev/null)
        
        if [ -n "$rds_sgs" ]; then
            log_info "RDS security groups: $rds_sgs"
            
            # Check PostgreSQL port access
            for sg in $rds_sgs; do
                local pg_rules=$(aws ec2 describe-security-groups \
                    --group-ids "$sg" \
                    --region "$AWS_REGION" \
                    --query "SecurityGroups[0].IpPermissions[?FromPort==\`5432\`]" 2>/dev/null)
                
                if [ "$pg_rules" != "[]" ] && [ -n "$pg_rules" ]; then
                    log_success "RDS security group has PostgreSQL port rules"
                else
                    log_error "RDS security group missing PostgreSQL port rules"
                fi
            done
        fi
    fi
    
    # ElastiCache security group
    if [ -n "$REDIS_ENDPOINT" ]; then
        local redis_cluster_id=$(echo "$REDIS_ENDPOINT" | cut -d'.' -f1)
        local redis_sgs=$(aws elasticache describe-cache-clusters \
            --cache-cluster-id "$redis_cluster_id" \
            --region "$AWS_REGION" \
            --query 'CacheClusters[0].SecurityGroups[].SecurityGroupId' \
            --output text 2>/dev/null)
        
        if [ -n "$redis_sgs" ] && [ "$redis_sgs" != "None" ]; then
            log_info "Redis security groups: $redis_sgs"
            
            # Check Redis port access
            for sg in $redis_sgs; do
                local redis_rules=$(aws ec2 describe-security-groups \
                    --group-ids "$sg" \
                    --region "$AWS_REGION" \
                    --query "SecurityGroups[0].IpPermissions[?FromPort==\`6379\`]" 2>/dev/null)
                
                if [ "$redis_rules" != "[]" ] && [ -n "$redis_rules" ]; then
                    log_success "Redis security group has Redis port rules"
                else
                    log_error "Redis security group missing Redis port rules"
                fi
            done
        fi
    fi
    
    return 0
}

test_network_acls() {
    # Check network ACLs
    local nacls=$(aws ec2 describe-network-acls \
        --filters "Name=vpc-id,Values=$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'NetworkAcls[].NetworkAclId' \
        --output text 2>/dev/null)
    
    if [ -n "$nacls" ]; then
        local nacl_count=$(echo "$nacls" | wc -w)
        log_info "Found $nacl_count network ACL(s)"
        
        # Check for non-default NACLs
        local custom_nacls=0
        for nacl_id in $nacls; do
            local is_default=$(aws ec2 describe-network-acls \
                --network-acl-ids "$nacl_id" \
                --region "$AWS_REGION" \
                --query 'NetworkAcls[0].IsDefault' \
                --output text 2>/dev/null)
            
            if [ "$is_default" = "false" ]; then
                custom_nacls=$((custom_nacls + 1))
                log_info "Custom network ACL found: $nacl_id"
            fi
        done
        
        if [ "$custom_nacls" -gt 0 ]; then
            log_info "Using $custom_nacls custom network ACL(s)"
        else
            log_info "Using default network ACLs only"
        fi
        
        return 0
    else
        log_error "No network ACLs found"
        return 1
    fi
}

test_vpc_flow_logs() {
    # Check if VPC flow logs are enabled
    local flow_logs=$(aws ec2 describe-flow-logs \
        --filter "Name=resource-id,Values=$VPC_ID" \
        --region "$AWS_REGION" \
        --query 'FlowLogs[].FlowLogId' \
        --output text 2>/dev/null)
    
    if [ -n "$flow_logs" ] && [ "$flow_logs" != "None" ]; then
        log_success "VPC flow logs are enabled"
        
        # Get flow log details
        local flow_log_info=$(aws ec2 describe-flow-logs \
            --filter "Name=resource-id,Values=$VPC_ID" \
            --region "$AWS_REGION" 2>/dev/null)
        
        local log_status=$(echo "$flow_log_info" | jq -r '.FlowLogs[0].FlowLogStatus')
        local log_destination=$(echo "$flow_log_info" | jq -r '.FlowLogs[0].LogDestinationType')
        
        log_info "  Status: $log_status"
        log_info "  Destination: $log_destination"
        
        return 0
    else
        log_warning "VPC flow logs are not enabled"
        return 0  # Warning, not failure
    fi
}

# Main test execution
main() {
    log_info "Starting VPC and Network Security Tests..."
    echo "========================================="
    
    # Validate configuration
    if ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi
    
    # Run tests
    run_test "VPC exists and configured" test_vpc_exists
    run_test "Subnets configuration" test_subnets_configuration
    run_test "Internet gateway" test_internet_gateway
    run_test "NAT gateway configuration" test_nat_gateway
    run_test "Security groups baseline" test_security_groups_baseline
    run_test "Application security groups" test_application_security_groups
    run_test "Network ACLs" test_network_acls
    run_test "VPC flow logs" test_vpc_flow_logs
    
    # Print summary
    print_test_summary
}

# Execute main function
main "$@"