# Learning Schema Database Setup

This directory contains scripts and documentation for setting up the learning schema in the RDS PostgreSQL instance.

## Prerequisites

1. Python 3.x with psycopg2 installed
2. Database credentials for the RDS instance
3. Proper network access to the RDS instance

## Database Connection Test Script

### Purpose

The `test_learning_db_connection.py` script verifies:
- Connectivity to the RDS PostgreSQL instance
- Read access to existing Trac tables in the public schema
- Permissions to create schemas and tables
- UUID extension availability
- Current status of the learning schema

### Usage

1. **Set environment variables** (recommended):
   ```bash
   export DB_HOST="your-rds-endpoint.amazonaws.com"
   export DB_PORT="5432"
   export DB_NAME="learntrac"
   export DB_USER="your_db_user"
   export DB_PASSWORD="your_db_password"
   ```

2. **Run the test script**:
   ```bash
   python test_learning_db_connection.py
   ```

3. **Or use command line arguments**:
   ```bash
   python test_learning_db_connection.py \
     --host your-rds-endpoint.amazonaws.com \
     --port 5432 \
     --database learntrac \
     --user your_db_user \
     --password your_db_password
   ```

### Expected Output

The script will test various aspects and provide output like:
```
=== Learning Schema Database Connection Tests ===

--- Public Schema Access ---
✓ Can access public schema
✓ Can see ticket table in public schema
✓ Can read from public.ticket table (X records)

--- Schema Creation Permissions ---
✓ Can create schemas
✓ Can drop schemas

--- Table Creation Permissions ---
✓ Can create, write to, and read from tables

--- UUID Extension ---
✓ pgcrypto extension is already installed
✓ UUID generation works: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

--- Learning Schema Status ---
✓ Learning schema does not exist (ready to create)
```

### Connection Parameters

After successful testing, the script saves connection parameters to `connection_params.json` (excluding the password) for use by other scripts.

## Next Steps

After verifying connectivity and permissions:

1. Review the learning schema SQL in the parent task
2. Run the schema creation script (to be created)
3. Verify all tables and relationships are created correctly

## Security Notes

- Never commit database passwords to version control
- Use AWS Secrets Manager or environment variables for credentials
- Ensure RDS security groups only allow access from authorized sources
- Use SSL/TLS connections in production

## Troubleshooting

### Connection Refused
- Check RDS security group allows inbound traffic on port 5432
- Verify the RDS instance is publicly accessible (if connecting from outside VPC)
- Check the RDS endpoint is correct

### Permission Denied
- Ensure the database user has sufficient privileges
- May need to grant CREATE privilege: `GRANT CREATE ON DATABASE learntrac TO your_user;`

### UUID Extension Issues
- The pgcrypto extension may require superuser privileges to install
- Contact DBA or use RDS parameter groups to enable extensions