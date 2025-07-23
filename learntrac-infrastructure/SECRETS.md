# Secrets Management

This infrastructure uses AWS Secrets Manager to securely store sensitive credentials.

## Default Configuration

The infrastructure is pre-configured with the following secrets:

### Neo4j Database
- **Username**: `neo4j` (hardcoded)
- **Password**: Stored securely in AWS Secrets Manager
- **URI**: You need to provide your Neo4j instance URI

### OpenAI API Key
- Optional - only needed if using AI features
- Stored securely in AWS Secrets Manager

## How Secrets Work

1. **Terraform creates secrets** in AWS Secrets Manager during `terraform apply`
2. **ECS tasks** are granted permission to read these secrets
3. **Applications** receive secrets as environment variables at runtime
4. **No secrets are stored** in code or container images

## Updating Secrets

### Option 1: Through Terraform Variables
```bash
# Set in terraform.tfvars (don't commit this file!)
neo4j_uri      = "neo4j+s://your-instance.databases.neo4j.io"
neo4j_password = "your-new-password"
openai_api_key = "sk-..."
```

### Option 2: Directly in AWS Console
1. Go to AWS Secrets Manager
2. Find the secret (e.g., `hutch-learntrac-dev-neo4j-credentials`)
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update the values
6. Save changes

### Option 3: Using AWS CLI
```bash
aws secretsmanager update-secret \
  --secret-id hutch-learntrac-dev-neo4j-credentials \
  --secret-string '{
    "uri": "neo4j+s://your-instance.databases.neo4j.io",
    "username": "neo4j",
    "password": "your-new-password"
  }'
```

## Local Development

For local development, create a `.env` file in `learntrac-api/`:

```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OPENAI_API_KEY=sk-...
```

**Important**: Add `.env` to `.gitignore` to prevent accidental commits!

## Security Best Practices

1. **Never commit** passwords or API keys to git
2. **Use different passwords** for dev/staging/prod environments
3. **Rotate secrets** regularly
4. **Limit access** to AWS Secrets Manager using IAM policies
5. **Monitor access** using CloudTrail

## Viewing Current Secrets

After deployment, you can see the secret ARNs:

```bash
terraform output neo4j_secret_arn
terraform output openai_secret_arn
```

Then retrieve the actual values (requires appropriate AWS permissions):

```bash
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw neo4j_secret_arn) \
  --query SecretString \
  --output text | jq
```