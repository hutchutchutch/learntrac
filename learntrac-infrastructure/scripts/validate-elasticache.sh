#!/bin/bash

# ElastiCache Redis Validation Script
# This script validates the ElastiCache Redis configuration and connectivity

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "====================================="
echo "ElastiCache Redis Validation Script"
echo "====================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Get the cluster information
CLUSTER_ID="hutch-learntrac-dev-redis"
REGION="us-east-2"

echo "Fetching ElastiCache cluster information..."
echo ""

# Get cluster details
CLUSTER_INFO=$(aws elasticache describe-cache-clusters \
    --cache-cluster-id $CLUSTER_ID \
    --show-cache-node-info \
    --region $REGION 2>/dev/null || true)

if [ -z "$CLUSTER_INFO" ]; then
    echo -e "${RED}Error: Could not fetch cluster information${NC}"
    echo "Make sure you have the correct AWS credentials and permissions"
    exit 1
fi

# Extract cluster information
CLUSTER_STATUS=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].CacheClusterStatus')
ENGINE=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].Engine')
ENGINE_VERSION=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].EngineVersion')
NODE_TYPE=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].CacheNodeType')
ENDPOINT=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].CacheNodes[0].Endpoint.Address')
PORT=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].CacheNodes[0].Endpoint.Port')

echo -e "${GREEN}✓ Cluster Information:${NC}"
echo "  Cluster ID: $CLUSTER_ID"
echo "  Status: $CLUSTER_STATUS"
echo "  Engine: $ENGINE $ENGINE_VERSION"
echo "  Node Type: $NODE_TYPE"
echo "  Endpoint: $ENDPOINT:$PORT"
echo ""

# Check cluster status
if [ "$CLUSTER_STATUS" != "available" ]; then
    echo -e "${YELLOW}Warning: Cluster status is '$CLUSTER_STATUS', expected 'available'${NC}"
else
    echo -e "${GREEN}✓ Cluster is available${NC}"
fi
echo ""

# Get subnet group information
echo "Checking subnet group configuration..."
SUBNET_GROUP=$(aws elasticache describe-cache-subnet-groups \
    --cache-subnet-group-name "hutch-learntrac-dev-redis-subnet" \
    --region $REGION 2>/dev/null || true)

if [ ! -z "$SUBNET_GROUP" ]; then
    SUBNET_COUNT=$(echo $SUBNET_GROUP | jq '.CacheSubnetGroups[0].Subnets | length')
    echo -e "${GREEN}✓ Subnet group configured with $SUBNET_COUNT subnets${NC}"
else
    echo -e "${YELLOW}Warning: Could not fetch subnet group information${NC}"
fi
echo ""

# Get security group information
echo "Checking security group configuration..."
SECURITY_GROUPS=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].SecurityGroups[].SecurityGroupId' | tr '\n' ' ')
if [ ! -z "$SECURITY_GROUPS" ]; then
    echo -e "${GREEN}✓ Security groups attached: $SECURITY_GROUPS${NC}"
    
    # Check security group rules
    for SG in $SECURITY_GROUPS; do
        echo "  Checking rules for $SG..."
        INGRESS_RULES=$(aws ec2 describe-security-groups \
            --group-ids $SG \
            --region $REGION \
            --query 'SecurityGroups[0].IpPermissions[?FromPort==`6379`]' 2>/dev/null || true)
        
        if [ "$INGRESS_RULES" != "[]" ] && [ ! -z "$INGRESS_RULES" ]; then
            echo -e "  ${GREEN}✓ Port 6379 ingress rules configured${NC}"
        else
            echo -e "  ${YELLOW}Warning: No ingress rules found for port 6379${NC}"
        fi
    done
else
    echo -e "${YELLOW}Warning: No security groups found${NC}"
fi
echo ""

# Check parameter group
echo "Checking parameter group..."
PARAM_GROUP=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].CacheParameterGroup.CacheParameterGroupName')
echo -e "${GREEN}✓ Parameter group: $PARAM_GROUP${NC}"
echo ""

# Check snapshot configuration
echo "Checking backup configuration..."
SNAPSHOT_RETENTION=$(echo $CLUSTER_INFO | jq -r '.CacheClusters[0].SnapshotRetentionLimit')
if [ "$SNAPSHOT_RETENTION" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Snapshot retention is disabled (appropriate for dev)${NC}"
else
    echo -e "${GREEN}✓ Snapshot retention: $SNAPSHOT_RETENTION days${NC}"
fi
echo ""

# Performance metrics check
echo "Checking recent performance metrics..."
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%S)
START_TIME=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%S)

# CPU Utilization
CPU_METRIC=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/ElastiCache \
    --metric-name CPUUtilization \
    --dimensions Name=CacheClusterId,Value=$CLUSTER_ID \
    --statistics Average \
    --start-time $START_TIME \
    --end-time $END_TIME \
    --period 300 \
    --region $REGION 2>/dev/null || true)

if [ ! -z "$CPU_METRIC" ]; then
    AVG_CPU=$(echo $CPU_METRIC | jq -r '.Datapoints | if length > 0 then [.[].Average] | add/length else 0 end')
    if (( $(echo "$AVG_CPU > 0" | bc -l) )); then
        echo -e "${GREEN}✓ Average CPU Utilization (last hour): ${AVG_CPU}%${NC}"
    fi
fi

# Memory usage
MEMORY_METRIC=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/ElastiCache \
    --metric-name DatabaseMemoryUsagePercentage \
    --dimensions Name=CacheClusterId,Value=$CLUSTER_ID \
    --statistics Average \
    --start-time $START_TIME \
    --end-time $END_TIME \
    --period 300 \
    --region $REGION 2>/dev/null || true)

if [ ! -z "$MEMORY_METRIC" ]; then
    AVG_MEMORY=$(echo $MEMORY_METRIC | jq -r '.Datapoints | if length > 0 then [.[].Average] | add/length else 0 end')
    if (( $(echo "$AVG_MEMORY > 0" | bc -l) )); then
        echo -e "${GREEN}✓ Average Memory Usage (last hour): ${AVG_MEMORY}%${NC}"
    fi
fi
echo ""

# Generate connection test commands
echo "====================================="
echo "Connection Test Commands"
echo "====================================="
echo ""
echo "To test Redis connectivity from an ECS task or EC2 instance in the VPC:"
echo ""
echo "1. Install Redis CLI:"
echo "   sudo apt-get update && sudo apt-get install -y redis-tools"
echo ""
echo "2. Test connection:"
echo "   redis-cli -h $ENDPOINT -p $PORT ping"
echo ""
echo "3. Test basic operations:"
echo "   redis-cli -h $ENDPOINT -p $PORT"
echo "   > SET test \"Hello LearnTrac\""
echo "   > GET test"
echo "   > DEL test"
echo "   > QUIT"
echo ""

# Summary
echo "====================================="
echo "Validation Summary"
echo "====================================="
echo ""

ISSUES=0

if [ "$CLUSTER_STATUS" = "available" ]; then
    echo -e "${GREEN}✓ Cluster is operational${NC}"
else
    echo -e "${RED}✗ Cluster is not available${NC}"
    ((ISSUES++))
fi

if [ ! -z "$SECURITY_GROUPS" ]; then
    echo -e "${GREEN}✓ Security groups configured${NC}"
else
    echo -e "${RED}✗ No security groups found${NC}"
    ((ISSUES++))
fi

if [ "$ENGINE" = "redis" ]; then
    echo -e "${GREEN}✓ Redis engine confirmed${NC}"
else
    echo -e "${RED}✗ Unexpected engine: $ENGINE${NC}"
    ((ISSUES++))
fi

echo ""
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}All validation checks passed!${NC}"
else
    echo -e "${YELLOW}Found $ISSUES issue(s) that may need attention${NC}"
fi