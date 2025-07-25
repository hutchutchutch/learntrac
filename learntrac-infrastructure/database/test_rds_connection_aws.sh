#!/bin/bash
# Test RDS connection using AWS CLI and PostgreSQL client tools

# Database connection parameters
DB_HOST="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="learntrac"
DB_USER="learntrac_admin"
DB_PASSWORD="Vp-Sl}}D[(j&zxP5cjh%MTQtitYq2ic7"

echo "=== RDS Database Connection Test ==="
echo ""
echo "Testing connection to:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Test if psql is available
if ! command -v psql &> /dev/null; then
    echo "✗ psql command not found. Installing would require:"
    echo "  brew install postgresql (on macOS)"
    echo "  apt-get install postgresql-client (on Ubuntu/Debian)"
    echo ""
fi

# Test DNS resolution
echo "--- DNS Resolution Test ---"
if host $DB_HOST &> /dev/null; then
    echo "✓ DNS resolution successful"
    host $DB_HOST | head -n 1
else
    echo "✗ DNS resolution failed"
fi
echo ""

# Test network connectivity
echo "--- Network Connectivity Test ---"
if nc -zv -w 5 $DB_HOST $DB_PORT 2>&1 | grep -q "succeeded"; then
    echo "✓ Port $DB_PORT is accessible"
else
    echo "✗ Cannot connect to port $DB_PORT"
    echo "  This might be due to security group restrictions"
fi
echo ""

# Check AWS RDS instance status using AWS CLI
echo "--- AWS RDS Instance Status ---"
if command -v aws &> /dev/null; then
    INSTANCE_ID=$(echo $DB_HOST | cut -d'.' -f1)
    echo "Checking RDS instance: $INSTANCE_ID"
    
    aws rds describe-db-instances \
        --db-instance-identifier "$INSTANCE_ID" \
        --query 'DBInstances[0].[DBInstanceStatus,Engine,EngineVersion,PubliclyAccessible]' \
        --output text 2>/dev/null || echo "✗ Cannot retrieve RDS instance details (check AWS credentials)"
else
    echo "✗ AWS CLI not found. Cannot check RDS instance status."
fi
echo ""

# If psql is available, try to connect
if command -v psql &> /dev/null; then
    echo "--- PostgreSQL Connection Test ---"
    export PGPASSWORD="$DB_PASSWORD"
    
    # Test basic connection and get version
    echo "Testing database connection..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" 2>&1 | head -n 3
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully connected to database"
        echo ""
        
        # Check if learning schema exists
        echo "--- Learning Schema Status ---"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT CASE 
                WHEN EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning')
                THEN '✓ Learning schema exists'
                ELSE '✓ Learning schema does not exist (ready to create)'
            END;
        " 2>/dev/null
        
        # Check Trac tables
        echo ""
        echo "--- Trac Tables Check ---"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT COUNT(*) || ' tables found in public schema' 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        " 2>/dev/null
        
        # List some key Trac tables if they exist
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
            SELECT string_agg(table_name, ', ' ORDER BY table_name) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('ticket', 'wiki', 'system', 'permission', 'milestone')
            LIMIT 10;
        " 2>/dev/null | sed 's/^/  Key tables: /'
        
    else
        echo "✗ Failed to connect to database"
        echo "  Check credentials and network access"
    fi
    
    unset PGPASSWORD
else
    echo "--- PostgreSQL Client Test Skipped ---"
    echo "✗ psql not available. Install postgresql client tools to run full tests."
fi

echo ""
echo "=== Summary ==="
echo "Use the Python test script with proper psycopg2 installation for comprehensive testing."
echo "Or use Docker/container with PostgreSQL client tools pre-installed."