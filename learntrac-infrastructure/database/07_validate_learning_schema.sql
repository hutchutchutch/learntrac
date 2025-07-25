-- Learning Schema Validation Script
-- This script validates the learning schema structure and relationships

\echo '==================================================='
\echo 'Learning Schema Validation Report'
\echo '==================================================='
\echo ''

-- Check if learning schema exists
DO $$
DECLARE
    schema_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning'
    ) INTO schema_exists;
    
    IF NOT schema_exists THEN
        RAISE EXCEPTION 'VALIDATION FAILED: Learning schema does not exist';
    ELSE
        RAISE NOTICE 'PASS: Learning schema exists';
    END IF;
END $$;

-- Validate UUID extension
DO $$
DECLARE
    extension_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'
    ) INTO extension_exists;
    
    IF NOT extension_exists THEN
        RAISE WARNING 'UUID extension uuid-ossp is not installed';
    ELSE
        RAISE NOTICE 'PASS: UUID extension is available';
    END IF;
END $$;

\echo ''
\echo '--- Table Structure Validation ---'

-- Validate all required tables exist
WITH required_tables AS (
    SELECT unnest(ARRAY[
        'paths',
        'concept_metadata',
        'prerequisites',
        'path_concepts',
        'progress',
        'resources',
        'activities'
    ]) AS table_name
),
existing_tables AS (
    SELECT tablename AS table_name
    FROM pg_tables
    WHERE schemaname = 'learning'
)
SELECT 
    rt.table_name,
    CASE 
        WHEN et.table_name IS NOT NULL THEN 'EXISTS'
        ELSE 'MISSING'
    END AS status
FROM required_tables rt
LEFT JOIN existing_tables et ON rt.table_name = et.table_name
ORDER BY rt.table_name;

\echo ''
\echo '--- Column Validation ---'

-- Validate paths table columns
\echo 'Table: learning.paths'
SELECT 
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'learning' AND table_name = 'paths'
ORDER BY ordinal_position;

\echo ''
\echo '--- Primary Key Validation ---'

-- Check primary keys
SELECT 
    tc.table_name,
    kcu.column_name,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
AND tc.table_schema = 'learning'
ORDER BY tc.table_name;

\echo ''
\echo '--- Foreign Key Validation ---'

-- Check foreign keys
SELECT 
    tc.table_name AS child_table,
    kcu.column_name AS child_column,
    ccu.table_name AS parent_table,
    ccu.column_name AS parent_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'learning'
ORDER BY tc.table_name, kcu.column_name;

\echo ''
\echo '--- Index Validation ---'

-- Check indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'learning'
ORDER BY tablename, indexname;

\echo ''
\echo '--- Constraint Validation ---'

-- Check constraints
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    cc.check_clause
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.check_constraints cc
    ON tc.constraint_name = cc.constraint_name
    AND tc.constraint_schema = cc.constraint_schema
WHERE tc.table_schema = 'learning'
AND tc.constraint_type IN ('CHECK', 'UNIQUE')
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;

\echo ''
\echo '--- Trigger Validation ---'

-- Check triggers
SELECT 
    trigger_name,
    event_object_table,
    event_manipulation,
    action_timing
FROM information_schema.triggers
WHERE trigger_schema = 'learning'
ORDER BY event_object_table, trigger_name;

\echo ''
\echo '--- Permission Validation ---'

-- Check permissions for learntrac_app user
DO $$
DECLARE
    user_exists BOOLEAN;
    schema_usage BOOLEAN;
    table_count INTEGER;
    permitted_tables INTEGER;
BEGIN
    -- Check if user exists
    SELECT EXISTS (
        SELECT 1 FROM pg_user WHERE usename = 'learntrac_app'
    ) INTO user_exists;
    
    IF NOT user_exists THEN
        RAISE WARNING 'User learntrac_app does not exist';
    ELSE
        -- Check schema usage permission
        SELECT EXISTS (
            SELECT 1 FROM information_schema.schema_privileges
            WHERE grantee = 'learntrac_app' 
            AND table_schema = 'learning'
            AND privilege_type = 'USAGE'
        ) INTO schema_usage;
        
        IF schema_usage THEN
            RAISE NOTICE 'PASS: User learntrac_app has USAGE permission on learning schema';
        ELSE
            RAISE WARNING 'User learntrac_app lacks USAGE permission on learning schema';
        END IF;
        
        -- Check table permissions
        SELECT COUNT(*) INTO table_count
        FROM pg_tables WHERE schemaname = 'learning';
        
        SELECT COUNT(DISTINCT table_name) INTO permitted_tables
        FROM information_schema.table_privileges
        WHERE grantee = 'learntrac_app' 
        AND table_schema = 'learning'
        AND privilege_type IN ('SELECT', 'INSERT', 'UPDATE', 'DELETE');
        
        RAISE NOTICE 'User learntrac_app has permissions on % out of % tables', 
                     permitted_tables, table_count;
    END IF;
END $$;

\echo ''
\echo '--- Data Integrity Checks ---'

-- Check for orphaned prerequisites
SELECT COUNT(*) AS orphaned_prerequisites
FROM learning.prerequisites p
WHERE NOT EXISTS (
    SELECT 1 FROM learning.concept_metadata c 
    WHERE c.id = p.concept_id
) OR NOT EXISTS (
    SELECT 1 FROM learning.concept_metadata c 
    WHERE c.id = p.prerequisite_concept_id
);

-- Check for circular prerequisites
WITH RECURSIVE prerequisite_chain AS (
    SELECT 
        concept_id,
        prerequisite_concept_id,
        ARRAY[concept_id, prerequisite_concept_id] AS path
    FROM learning.prerequisites
    
    UNION ALL
    
    SELECT 
        pc.concept_id,
        p.prerequisite_concept_id,
        pc.path || p.prerequisite_concept_id
    FROM prerequisite_chain pc
    JOIN learning.prerequisites p ON pc.prerequisite_concept_id = p.concept_id
    WHERE NOT p.prerequisite_concept_id = ANY(pc.path)
)
SELECT 
    'Circular dependency detected' AS issue,
    path
FROM prerequisite_chain
WHERE concept_id = prerequisite_concept_id;

-- Check for duplicate path sequences
SELECT 
    path_id,
    sequence_order,
    COUNT(*) as duplicate_count
FROM learning.path_concepts
GROUP BY path_id, sequence_order
HAVING COUNT(*) > 1;

\echo ''
\echo '--- Summary Statistics ---'

-- Count records in each table
SELECT 
    'learning.' || tablename AS table_name,
    n_live_tup AS row_count,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size
FROM pg_stat_user_tables
WHERE schemaname = 'learning'
ORDER BY tablename;

\echo ''
\echo '--- Validation Complete ---'

-- Final validation summary
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    fk_count INTEGER;
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count 
    FROM pg_tables WHERE schemaname = 'learning';
    
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes WHERE schemaname = 'learning';
    
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints
    WHERE table_schema = 'learning' AND constraint_type = 'FOREIGN KEY';
    
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE trigger_schema = 'learning';
    
    RAISE NOTICE 'Learning Schema Summary:';
    RAISE NOTICE '  Tables: %', table_count;
    RAISE NOTICE '  Indexes: %', index_count;
    RAISE NOTICE '  Foreign Keys: %', fk_count;
    RAISE NOTICE '  Triggers: %', trigger_count;
    
    IF table_count >= 7 AND index_count >= 10 AND fk_count >= 5 THEN
        RAISE NOTICE 'VALIDATION PASSED: Learning schema is properly configured';
    ELSE
        RAISE WARNING 'VALIDATION WARNING: Some expected objects may be missing';
    END IF;
END $$;