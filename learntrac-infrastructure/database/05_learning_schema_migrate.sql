-- Learning Schema Migration Script
-- This script handles the migration process for the learning schema
-- It checks for existing objects and migrates data if necessary

-- Start transaction for atomic migration
BEGIN;

-- Check if learning schema exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'learning') THEN
        RAISE NOTICE 'Learning schema does not exist. Running full initialization...';
        -- The main init script will handle creation
    ELSE
        RAISE NOTICE 'Learning schema exists. Checking for updates...';
    END IF;
END $$;

-- Migration helper function to safely add columns
CREATE OR REPLACE FUNCTION learning.safe_add_column(
    p_schema_name TEXT,
    p_table_name TEXT,
    p_column_name TEXT,
    p_column_definition TEXT
) RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = p_schema_name 
        AND table_name = p_table_name 
        AND column_name = p_column_name
    ) THEN
        EXECUTE format('ALTER TABLE %I.%I ADD COLUMN %I %s',
            p_schema_name, p_table_name, p_column_name, p_column_definition);
        RAISE NOTICE 'Added column %.% to %.%', p_column_name, p_column_definition, p_schema_name, p_table_name;
    ELSE
        RAISE NOTICE 'Column %.% already exists in %.%', p_column_name, p_column_definition, p_schema_name, p_table_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Migration 1: Add metadata columns if they don't exist
SELECT learning.safe_add_column('learning', 'paths', 'metadata', 'JSONB DEFAULT ''{}''::jsonb');
SELECT learning.safe_add_column('learning', 'concept_metadata', 'metadata', 'JSONB DEFAULT ''{}''::jsonb');
SELECT learning.safe_add_column('learning', 'progress', 'assessment_scores', 'JSONB DEFAULT ''[]''::jsonb');

-- Migration 2: Add missing indexes
DO $$
BEGIN
    -- Check and create index on activities created_at if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'learning' 
        AND tablename = 'activities' 
        AND indexname = 'idx_activities_created_at'
    ) THEN
        CREATE INDEX idx_activities_created_at ON learning.activities(created_at);
        RAISE NOTICE 'Created index idx_activities_created_at';
    END IF;
END $$;

-- Migration 3: Update any deprecated column types or constraints
-- Example: Ensure UUID columns are using uuid-ossp extension
DO $$
BEGIN
    -- Ensure uuid-ossp extension is available
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Add any specific column type migrations here
END $$;

-- Migration 4: Data migration examples
-- Migrate any existing learning data from old structure to new structure
DO $$
BEGIN
    -- Example: If migrating from an older schema version
    -- This is a placeholder for actual data migration logic
    
    -- Check if old tables exist and migrate data
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'public' AND table_name = 'old_learning_paths') THEN
        RAISE NOTICE 'Migrating data from old_learning_paths...';
        -- INSERT INTO learning.paths (columns...) 
        -- SELECT columns... FROM public.old_learning_paths;
    END IF;
END $$;

-- Migration 5: Update permissions for new objects
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Grant permissions on any new tables to the application user
    FOR r IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'learning'
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON learning.%I TO learntrac_app', r.tablename);
    END LOOP;
    
    -- Grant permissions on any new sequences
    FOR r IN 
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'learning'
    LOOP
        EXECUTE format('GRANT USAGE, SELECT ON learning.%I TO learntrac_app', r.sequence_name);
    END LOOP;
END $$;

-- Migration 6: Update trigger functions if needed
CREATE OR REPLACE FUNCTION learning.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Record migration completion
DO $$
BEGIN
    -- Create migration tracking table if it doesn't exist
    CREATE TABLE IF NOT EXISTS learning.schema_migrations (
        id SERIAL PRIMARY KEY,
        version VARCHAR(50) NOT NULL UNIQUE,
        description TEXT,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Record this migration
    INSERT INTO learning.schema_migrations (version, description) 
    VALUES ('1.0.0', 'Initial learning schema with paths, concepts, prerequisites, and progress tracking')
    ON CONFLICT (version) DO NOTHING;
END $$;

-- Clean up migration helper function
DROP FUNCTION IF EXISTS learning.safe_add_column(TEXT, TEXT, TEXT, TEXT);

-- Commit the migration
COMMIT;

-- Display migration summary
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'learning' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE schemaname = 'learning';
    
    RAISE NOTICE 'Migration completed successfully:';
    RAISE NOTICE '  - Tables in learning schema: %', table_count;
    RAISE NOTICE '  - Indexes in learning schema: %', index_count;
END $$;