#!/bin/bash
# Script to list all Hutch's LearnTrac resources in AWS

OWNER="hutch"
PROJECT="learntrac"
ENVIRONMENT="dev"
PREFIX="${OWNER}-${PROJECT}-${ENVIRONMENT}"

echo "=== Hutch's LearnTrac AWS Resources ==="
echo "Owner: $OWNER"
echo "Project: $PROJECT"
echo "Environment: $ENVIRONMENT"
echo "Prefix: $PREFIX"
echo ""

echo "=== RDS Instances ==="
aws rds describe-db-instances \
  --query "DBInstances[?contains(DBInstanceIdentifier, '${PREFIX}')].[DBInstanceIdentifier, DBInstanceStatus, Engine, EngineVersion]" \
  --output table

echo -e "\n=== Security Groups ==="
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=${PREFIX}-*" \
  --query "SecurityGroups[*].[GroupName, GroupId, Description]" \
  --output table

echo -e "\n=== DB Subnet Groups ==="
aws rds describe-db-subnet-groups \
  --query "DBSubnetGroups[?contains(DBSubnetGroupName, '${PREFIX}')].[DBSubnetGroupName, VpcId]" \
  --output table

echo -e "\n=== Secrets Manager Secrets ==="
aws secretsmanager list-secrets \
  --query "SecretList[?contains(Name, '${PREFIX}')].[Name, ARN]" \
  --output table