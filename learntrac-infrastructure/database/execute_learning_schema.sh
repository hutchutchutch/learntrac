#!/bin/bash
# Execute the learning schema creation script

# Database connection parameters
DB_HOST="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="learntrac"
DB_USER="learntrac_admin"
DB_PASSWORD="Vp-Sl}}D[(j&zxP5cjh%MTQtitYq2ic7"

# Script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="$SCRIPT_DIR/create_learning_schema.sql"

echo "=== Learning Schema Creation ==="
echo ""
echo "This script will create the learning schema and all required tables."
echo "Database: $DB_NAME on $DB_HOST"
echo ""

# Check if SQL file exists
if [ ! -f "$SQL_FILE" ]; then
    echo "✗ SQL file not found: $SQL_FILE"
    exit 1
fi

# Export password for psql
export PGPASSWORD="$DB_PASSWORD"

# Execute the SQL script
echo "Executing schema creation script..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Schema creation completed successfully!"
    echo ""
    
    # Verify the schema was created
    echo "=== Verification ==="
    echo ""
    
    echo "--- Schemas ---"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = 'learning';
    "
    
    echo ""
    echo "--- Tables Created ---"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'learning' 
        ORDER BY table_name;
    "
    
    echo ""
    echo "--- Foreign Key Constraints ---"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT 
            tc.table_name || '.' || kcu.column_name || ' -> ' || 
            ccu.table_schema || '.' || ccu.table_name || '.' || ccu.column_name AS constraint_definition
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = 'learning' 
        AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.column_name;
    "
    
    echo ""
    echo "--- Indexes Created ---"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'learning' 
        ORDER BY tablename, indexname;
    "
    
    echo ""
    echo "--- Views Created ---"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT table_name 
        FROM information_schema.views 
        WHERE table_schema = 'learning' 
        ORDER BY table_name;
    "
    
    echo ""
    echo "=== Summary ==="
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT 
            COUNT(DISTINCT table_name) || ' tables' AS count
        FROM information_schema.tables 
        WHERE table_schema = 'learning' AND table_type = 'BASE TABLE'
        UNION ALL
        SELECT 
            COUNT(DISTINCT table_name) || ' views'
        FROM information_schema.views 
        WHERE table_schema = 'learning'
        UNION ALL
        SELECT 
            COUNT(DISTINCT indexname) || ' indexes'
        FROM pg_indexes 
        WHERE schemaname = 'learning'
        UNION ALL
        SELECT 
            COUNT(*) || ' foreign key constraints'
        FROM information_schema.table_constraints
        WHERE table_schema = 'learning' 
        AND constraint_type = 'FOREIGN KEY';
    "
    
else
    echo ""
    echo "✗ Schema creation failed!"
    echo "Check the error messages above for details."
    exit 1
fi

# Clean up
unset PGPASSWORD

echo ""
echo "=== Next Steps ==="
echo "1. Test the foreign key relationships with sample data"
echo "2. Run the migration script if needed"
echo "3. Document the schema in the project documentation"