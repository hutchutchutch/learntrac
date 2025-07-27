# LearnTrac AWS Launch Guide

## Quick Start

```bash
./launch-with-aws.sh
```

This script will:
1. Check Docker and AWS CLI are configured
2. Fetch credentials from AWS Secrets Manager
3. Build the PDF upload plugin
4. Start Trac and Learning API containers
5. Connect to AWS services (RDS, ElastiCache, Neo4j)
6. Verify all connections

## Prerequisites

- Docker installed and running
- AWS CLI configured (`aws configure`)
- Access to AWS Secrets Manager secrets:
  - `hutch-learntrac-dev-db-credentials`
  - `hutch-learntrac-dev-neo4j-credentials` (optional)

## Services

### AWS Services Connected
- **RDS PostgreSQL**: Main database for Trac and learning data
- **ElastiCache Redis**: Session management, caching, rate limiting
- **Neo4j Aura**: Graph database for textbook content (if configured)

### Local Services
- **Trac Wiki** (http://localhost:8000): Wiki system with PDF upload
- **Learning API** (http://localhost:8001): API for textbook management

## Testing the Wiki Macros

1. Go to http://localhost:8000/wiki
2. Create a new wiki page
3. Add these macros:
   ```
   = My Textbooks Page =
   
   == Upload a New Textbook
   [[PDFUpload]]
   
   == Available Textbooks
   [[TextbookList]]
   ```
4. Save the page to see the components

## Troubleshooting

### Check logs
```bash
docker compose -f docker-compose.aws.yml logs -f
```

### Restart services
```bash
docker compose -f docker-compose.aws.yml restart
```

### Stop services
```bash
docker compose -f docker-compose.aws.yml down
```

### Neo4j Connection Issues
If Neo4j credentials are not found, the system will use mock data. To add Neo4j:
1. Store credentials in AWS Secrets Manager as `hutch-learntrac-dev-neo4j-credentials`
2. Include: `uri`, `username`, `password` fields
3. Re-run `./launch-with-aws.sh`

### AWS Connection Issues
- Ensure AWS CLI is configured: `aws configure`
- Check IAM permissions for Secrets Manager
- Verify network connectivity to AWS services