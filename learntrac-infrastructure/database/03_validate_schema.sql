-- Trac Schema Validation Script
-- This script validates that all required tables and data have been created

SET search_path TO trac, public;

-- Check if all required tables exist
WITH required_tables AS (
    SELECT unnest(ARRAY[
        'system', 'component', 'enum', 'milestone', 'version',
        'ticket', 'ticket_change', 'ticket_custom', 'attachment',
        'wiki', 'permission', 'auth_cookie', 'session',
        'session_attribute', 'cache', 'node_change', 'repository',
        'revision', 'report', 'notify_subscription', 'notify_watch'
    ]) AS table_name
),
existing_tables AS (
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'trac'
)
SELECT 
    rt.table_name,
    CASE 
        WHEN et.table_name IS NOT NULL THEN 'EXISTS'
        ELSE 'MISSING'
    END AS status
FROM required_tables rt
LEFT JOIN existing_tables et ON rt.table_name = et.table_name
ORDER BY 
    CASE WHEN et.table_name IS NULL THEN 0 ELSE 1 END,
    rt.table_name;

-- Check row counts for key tables
SELECT '=== Table Row Counts ===' AS info;
SELECT 'system' AS table_name, COUNT(*) AS row_count FROM system
UNION ALL
SELECT 'enum', COUNT(*) FROM enum
UNION ALL
SELECT 'permission', COUNT(*) FROM permission
UNION ALL
SELECT 'wiki', COUNT(*) FROM wiki
UNION ALL
SELECT 'report', COUNT(*) FROM report
UNION ALL
SELECT 'component', COUNT(*) FROM component
UNION ALL
SELECT 'milestone', COUNT(*) FROM milestone
UNION ALL
SELECT 'version', COUNT(*) FROM version
ORDER BY table_name;

-- Check if default enumerations exist
SELECT '=== Default Enumerations ===' AS info;
SELECT type, COUNT(*) AS count
FROM enum
GROUP BY type
ORDER BY type;

-- Check if admin permissions exist
SELECT '=== Admin Permissions ===' AS info;
SELECT COUNT(*) AS admin_permission_count
FROM permission
WHERE username = 'admin';

-- Check database version
SELECT '=== Database Version ===' AS info;
SELECT name, value
FROM system
WHERE name = 'database_version';

-- Check indexes
SELECT '=== Key Indexes ===' AS info;
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'trac'
AND indexname IN (
    'ticket_time_idx',
    'ticket_changetime_idx',
    'ticket_status_idx',
    'ticket_owner_idx',
    'ticket_reporter_idx',
    'wiki_time_idx',
    'session_last_visit_idx'
)
ORDER BY tablename, indexname;

-- Summary validation
SELECT '=== Validation Summary ===' AS info;
WITH validation_checks AS (
    SELECT 'Tables Created' AS check_name, 
           COUNT(*) AS actual,
           21 AS expected
    FROM information_schema.tables
    WHERE table_schema = 'trac'
    
    UNION ALL
    
    SELECT 'Enum Types' AS check_name,
           COUNT(DISTINCT type) AS actual,
           4 AS expected
    FROM enum
    
    UNION ALL
    
    SELECT 'Admin Permissions' AS check_name,
           COUNT(*) AS actual,
           35 AS expected  -- Approximate, may vary
    FROM permission
    WHERE username = 'admin'
    
    UNION ALL
    
    SELECT 'Default Reports' AS check_name,
           COUNT(*) AS actual,
           2 AS expected
    FROM report
    WHERE id IN (1, 2)
)
SELECT 
    check_name,
    actual,
    expected,
    CASE 
        WHEN actual >= expected THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM validation_checks
ORDER BY check_name;