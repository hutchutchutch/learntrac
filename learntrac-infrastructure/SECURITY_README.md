# LearnTrac Security Configuration Guide

## Overview

This guide documents the security configurations for the LearnTrac infrastructure, including VPC setup, security groups, and network isolation measures.

## Quick Start

### 1. Apply Security Updates

To apply the recommended security updates:

```bash
# Review planned changes
terraform plan -out=security-updates.tfplan

# Apply security updates
terraform apply security-updates.tfplan
```

### 2. Validate Security Configuration

Run the validation scripts:

```bash
# Check all security groups
./scripts/validate_security_groups.sh

# Test network connectivity
./scripts/test_network_connectivity.sh
```

## Security Architecture

### Network Isolation

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │   ALB   │ (Public Subnets)
                    └────┬────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   ┌────┴────┐                      ┌────┴────┐
   │  Trac   │                      │LearnTrac│ (Private Subnets)
   │  ECS    │                      │   API   │
   └────┬────┘                      └────┬────┘
        │                                 │
        ├─────────┬──────────────────────┤
        │         │                      │
   ┌────┴────┐ ┌──┴──┐           ┌──────┴──────┐
   │   RDS   │ │Redis│           │VPC Endpoints│
   └─────────┘ └─────┘           └─────────────┘
```

### Security Groups

| Component | Ingress | Egress | Purpose |
|-----------|---------|--------|---------|
| ALB | 80, 443 from 0.0.0.0/0 | All | Public web access |
| ECS Tasks | From ALB only | All | Application services |
| RDS | 5432 from ECS + Dev IP | All | Database access |
| Redis | 6379 from ECS | All | Cache access |
| VPC Endpoints | 443 from VPC CIDR | All | AWS service access |

## Security Features

### Enabled by Default
- ✅ VPC Flow Logs - Network traffic monitoring
- ✅ Security Groups - Port-level access control
- ✅ Encrypted RDS Storage - Data at rest encryption
- ✅ Secrets Manager - Secure credential storage
- ✅ VPC Endpoints - Private AWS service access

### Optional Features (Disabled by Default)
- ⬜ AWS WAF - Web application firewall
- ⬜ GuardDuty - Threat detection
- ⬜ Network ACLs - Subnet-level security
- ⬜ Security Hub - Compliance monitoring
- ⬜ AWS Config - Configuration tracking

To enable optional features, update `terraform.tfvars`:

```hcl
enable_waf          = true
enable_guardduty    = true
enable_network_acls = true
enable_security_hub = true
enable_aws_config   = true
```

## Security Improvements Applied

### 1. ECS to RDS Access
Added security group rules allowing ECS services to access RDS:
- Trac service → RDS (port 5432)
- LearnTrac API service → RDS (port 5432)

### 2. VPC Flow Logs
Enabled by default for network traffic analysis:
- Logs all accepted and rejected traffic
- 7-day retention for dev, 30-day for prod
- CloudWatch Logs destination

### 3. WAF Configuration (Optional)
When enabled, provides:
- Rate limiting (2000 requests/5 minutes per IP)
- SQL injection protection
- Common attack protection (OWASP Top 10)

## Validation and Testing

### Security Group Validation
```bash
# Validate all security groups exist and are configured correctly
./scripts/validate_security_groups.sh

# Expected output:
# ✓ All security groups validated
# ✓ No unexpected public access
# ✓ All components have proper security groups
```

### Network Connectivity Test
```bash
# Test connectivity between components
./scripts/test_network_connectivity.sh

# Tests include:
# - ALB public accessibility
# - RDS access from local (if public)
# - VPC endpoint availability
# - Security group rule validation
```

## Monitoring and Alerts

### CloudWatch Alarms (Configured)
- Unauthorized API calls
- Failed authentication attempts
- Unusual network traffic patterns

### VPC Flow Logs Analysis
Query examples for CloudWatch Insights:
```sql
-- Top rejected connections
fields srcaddr, dstport, protocol, action
| filter action = "REJECT"
| stats count(*) by srcaddr, dstport
| sort count desc

-- Traffic to RDS
fields @timestamp, srcaddr, dstaddr, dstport, action
| filter dstport = 5432
| sort @timestamp desc
```

## Best Practices Implemented

1. **Least Privilege Access**: Each component only has required access
2. **Defense in Depth**: Multiple security layers (SG, NACL, WAF)
3. **Encryption**: Data encrypted at rest and in transit
4. **Monitoring**: Comprehensive logging and alerting
5. **Private Communication**: VPC endpoints for AWS services

## Troubleshooting

### Common Issues

1. **ECS Cannot Connect to RDS**
   - Verify security group rules are applied
   - Check ECS task has correct security group
   - Ensure RDS is in available state

2. **VPC Endpoints Not Working**
   - Verify endpoint state is "available"
   - Check security group allows HTTPS (443)
   - Ensure private DNS is enabled

3. **Flow Logs Not Appearing**
   - Check IAM role has correct permissions
   - Verify CloudWatch log group exists
   - Wait 5-10 minutes for initial logs

## Security Checklist

Before deploying to production:

- [ ] Remove developer IP from RDS security group
- [ ] Enable WAF for public-facing ALB
- [ ] Enable GuardDuty for threat detection
- [ ] Configure Security Hub for compliance
- [ ] Review and tighten egress rules
- [ ] Enable MFA for AWS account access
- [ ] Rotate all secrets and passwords
- [ ] Configure backup encryption keys
- [ ] Enable CloudTrail for audit logs
- [ ] Set up SNS alerts for security events

## Additional Resources

- [AWS VPC Security Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html)
- [AWS Security Hub User Guide](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)
- [AWS WAF Developer Guide](https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html)