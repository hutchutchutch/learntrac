-- Learning Schema Rollback Script
-- This script safely removes the learning schema and all its objects
-- Use with caution - this will delete all learning data!

-- Prompt for confirmation (when run interactively)
\echo 'WARNING: This script will DROP the entire learning schema and ALL its data!'
\echo 'Press Ctrl+C to cancel, or Enter to continue...'
\prompt 'Continue? ' confirm

-- Start transaction for atomic rollback
BEGIN;

-- Record rollback attempt
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning') THEN
        -- Log the rollback if migrations table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables 
                   WHERE table_schema = 'learning' AND table_name = 'schema_migrations') THEN
            INSERT INTO learning.schema_migrations (version, description) 
            VALUES ('ROLLBACK-' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD-HH24MISS'), 
                    'Rollback initiated for learning schema');
        END IF;
    END IF;
END $$;

-- Drop dependent objects first
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop all views in learning schema
    FOR r IN 
        SELECT viewname 
        FROM pg_views 
        WHERE schemaname = 'learning'
    LOOP
        EXECUTE format('DROP VIEW IF EXISTS learning.%I CASCADE', r.viewname);
        RAISE NOTICE 'Dropped view: learning.%', r.viewname;
    END LOOP;
    
    -- Drop all functions in learning schema
    FOR r IN 
        SELECT proname, oidvectortypes(proargtypes) as argtypes 
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'learning'
    LOOP
        EXECUTE format('DROP FUNCTION IF EXISTS learning.%I(%s) CASCADE', r.proname, r.argtypes);
        RAISE NOTICE 'Dropped function: learning.%(%)', r.proname, r.argtypes;
    END LOOP;
    
    -- Drop all triggers
    FOR r IN 
        SELECT DISTINCT trigger_name, event_object_table 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'learning'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON learning.%I CASCADE', 
                       r.trigger_name, r.event_object_table);
        RAISE NOTICE 'Dropped trigger: % on learning.%', r.trigger_name, r.event_object_table;
    END LOOP;
END $$;

-- Optional: Backup data before dropping (uncomment if needed)
/*
DO $$
BEGIN
    -- Create backup schema
    CREATE SCHEMA IF NOT EXISTS learning_backup;
    
    -- Copy all tables to backup schema
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'learning'
    LOOP
        EXECUTE format('CREATE TABLE learning_backup.%I AS SELECT * FROM learning.%I', 
                       r.tablename || '_' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD'), 
                       r.tablename);
        RAISE NOTICE 'Backed up table: learning.% to learning_backup.%', 
                     r.tablename, r.tablename || '_' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD');
    END LOOP;
END $$;
*/

-- Revoke permissions
DO $$
BEGIN
    -- Revoke schema permissions
    EXECUTE 'REVOKE ALL ON SCHEMA learning FROM learntrac_app';
    EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA learning FROM learntrac_app';
    EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA learning FROM learntrac_app';
    EXECUTE 'REVOKE ALL ON ALL FUNCTIONS IN SCHEMA learning FROM learntrac_app';
    RAISE NOTICE 'Revoked all permissions from learntrac_app';
EXCEPTION
    WHEN undefined_object THEN
        RAISE NOTICE 'User learntrac_app does not exist, skipping permission revocation';
END $$;

-- Drop all tables in the correct order (respecting foreign key constraints)
DROP TABLE IF EXISTS learning.activities CASCADE;
DROP TABLE IF EXISTS learning.resources CASCADE;
DROP TABLE IF EXISTS learning.progress CASCADE;
DROP TABLE IF EXISTS learning.path_concepts CASCADE;
DROP TABLE IF EXISTS learning.prerequisites CASCADE;
DROP TABLE IF EXISTS learning.concept_metadata CASCADE;
DROP TABLE IF EXISTS learning.paths CASCADE;
DROP TABLE IF EXISTS learning.schema_migrations CASCADE;

-- Drop any remaining sequences
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'learning'
    LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS learning.%I CASCADE', r.sequence_name);
        RAISE NOTICE 'Dropped sequence: learning.%', r.sequence_name;
    END LOOP;
END $$;

-- Drop the schema
DROP SCHEMA IF EXISTS learning CASCADE;

-- Verify rollback
DO $$
DECLARE
    schema_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning'
    ) INTO schema_exists;
    
    IF schema_exists THEN
        RAISE EXCEPTION 'Rollback failed: learning schema still exists';
    ELSE
        RAISE NOTICE 'Rollback completed successfully: learning schema has been removed';
    END IF;
END $$;

-- Commit the rollback
COMMIT;

\echo 'Learning schema rollback completed successfully'
\echo 'All learning data has been removed'
\echo 'To restore, run: 04_learning_schema_init.sql'