-- =====================================================
-- Learning Schema Creation Script for LearnTrac
-- =====================================================
-- This script creates the learning schema and all required tables
-- for the LearnTrac learning path system alongside Trac tables
-- 
-- Prerequisites:
-- - PostgreSQL 15.x
-- - pgcrypto extension for UUID generation
-- - User with CREATE SCHEMA permissions
-- =====================================================

-- Start transaction for atomic execution
BEGIN;

-- =====================================================
-- 1. Create the learning schema
-- =====================================================
CREATE SCHEMA IF NOT EXISTS learning;

-- Grant usage on schema to the application user
-- (Adjust the username as needed for your setup)
GRANT USAGE ON SCHEMA learning TO learntrac_admin;
GRANT CREATE ON SCHEMA learning TO learntrac_admin;

-- =====================================================
-- 2. Ensure UUID extension is available
-- =====================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =====================================================
-- 3. Create learning.paths table
-- =====================================================
CREATE TABLE learning.paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    query_text TEXT,
    cognito_user_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_chunks INTEGER DEFAULT 0,
    question_difficulty INTEGER DEFAULT 3 CHECK (question_difficulty BETWEEN 1 AND 5)
);

-- Add comments for documentation
COMMENT ON TABLE learning.paths IS 'Stores learning paths created by users';
COMMENT ON COLUMN learning.paths.id IS 'Unique identifier for the learning path';
COMMENT ON COLUMN learning.paths.title IS 'User-friendly title for the learning path';
COMMENT ON COLUMN learning.paths.query_text IS 'Original query text used to generate the path';
COMMENT ON COLUMN learning.paths.cognito_user_id IS 'AWS Cognito user ID who created the path';
COMMENT ON COLUMN learning.paths.total_chunks IS 'Total number of chunks/concepts in this path';
COMMENT ON COLUMN learning.paths.question_difficulty IS 'Difficulty level for generated questions (1-5)';

-- =====================================================
-- 4. Create learning.concept_metadata table
-- =====================================================
CREATE TABLE learning.concept_metadata (
    ticket_id INTEGER PRIMARY KEY REFERENCES public.ticket(id) ON DELETE CASCADE,
    path_id UUID REFERENCES learning.paths(id) ON DELETE CASCADE,
    chunk_id VARCHAR(100) NOT NULL,
    relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),
    question_generated BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add comments
COMMENT ON TABLE learning.concept_metadata IS 'Links Trac tickets to learning paths with metadata';
COMMENT ON COLUMN learning.concept_metadata.ticket_id IS 'References the Trac ticket representing this concept';
COMMENT ON COLUMN learning.concept_metadata.path_id IS 'References the learning path this concept belongs to';
COMMENT ON COLUMN learning.concept_metadata.chunk_id IS 'Identifier from the source knowledge base chunk';
COMMENT ON COLUMN learning.concept_metadata.relevance_score IS 'Relevance score from vector search (0-1)';
COMMENT ON COLUMN learning.concept_metadata.question_generated IS 'Whether a question was successfully generated';

-- =====================================================
-- 5. Create learning.prerequisites table
-- =====================================================
CREATE TABLE learning.prerequisites (
    concept_ticket_id INTEGER REFERENCES public.ticket(id) ON DELETE CASCADE,
    prerequisite_ticket_id INTEGER REFERENCES public.ticket(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (concept_ticket_id, prerequisite_ticket_id),
    -- Ensure a ticket cannot be its own prerequisite
    CONSTRAINT no_self_prerequisite CHECK (concept_ticket_id != prerequisite_ticket_id)
);

-- Add comments
COMMENT ON TABLE learning.prerequisites IS 'Defines prerequisite relationships between learning concepts';
COMMENT ON COLUMN learning.prerequisites.concept_ticket_id IS 'The ticket that has prerequisites';
COMMENT ON COLUMN learning.prerequisites.prerequisite_ticket_id IS 'The ticket that is a prerequisite';

-- =====================================================
-- 6. Create learning.progress table
-- =====================================================
CREATE TABLE learning.progress (
    cognito_user_id VARCHAR(100) NOT NULL,
    ticket_id INTEGER REFERENCES public.ticket(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'mastered')),
    started_at TIMESTAMP,
    last_accessed TIMESTAMP,
    completed_at TIMESTAMP,
    time_spent_minutes INTEGER DEFAULT 0 CHECK (time_spent_minutes >= 0),
    notes TEXT,
    last_answer TEXT,
    answer_score FLOAT CHECK (answer_score >= 0 AND answer_score <= 1),
    answer_feedback TEXT,
    PRIMARY KEY (cognito_user_id, ticket_id)
);

-- Add comments
COMMENT ON TABLE learning.progress IS 'Tracks user progress through learning concepts';
COMMENT ON COLUMN learning.progress.cognito_user_id IS 'AWS Cognito user ID';
COMMENT ON COLUMN learning.progress.ticket_id IS 'The learning concept ticket';
COMMENT ON COLUMN learning.progress.status IS 'Current progress status';
COMMENT ON COLUMN learning.progress.answer_score IS 'Score from LLM evaluation (0-1)';

-- =====================================================
-- 7. Create indexes for performance
-- =====================================================

-- Indexes for learning.paths
CREATE INDEX idx_paths_cognito_user_id ON learning.paths(cognito_user_id);
CREATE INDEX idx_paths_created_at ON learning.paths(created_at DESC);

-- Indexes for learning.concept_metadata
CREATE INDEX idx_concept_metadata_path_id ON learning.concept_metadata(path_id);
CREATE INDEX idx_concept_metadata_chunk_id ON learning.concept_metadata(chunk_id);

-- Indexes for learning.prerequisites
CREATE INDEX idx_prerequisites_prerequisite_ticket_id ON learning.prerequisites(prerequisite_ticket_id);

-- Indexes for learning.progress
CREATE INDEX idx_progress_ticket_id ON learning.progress(ticket_id);
CREATE INDEX idx_progress_cognito_user_id ON learning.progress(cognito_user_id);
CREATE INDEX idx_progress_status ON learning.progress(status);
CREATE INDEX idx_progress_last_accessed ON learning.progress(last_accessed DESC);

-- =====================================================
-- 8. Create views for common queries
-- =====================================================

-- View: User learning paths with progress summary
CREATE VIEW learning.v_user_path_summary AS
SELECT 
    p.id AS path_id,
    p.title AS path_title,
    p.cognito_user_id,
    p.created_at,
    p.total_chunks,
    COUNT(DISTINCT cm.ticket_id) AS total_concepts,
    COUNT(DISTINCT CASE WHEN pr.status = 'completed' THEN pr.ticket_id END) AS completed_concepts,
    COUNT(DISTINCT CASE WHEN pr.status = 'mastered' THEN pr.ticket_id END) AS mastered_concepts,
    ROUND(
        CASE 
            WHEN COUNT(DISTINCT cm.ticket_id) > 0 
            THEN COUNT(DISTINCT CASE WHEN pr.status IN ('completed', 'mastered') THEN pr.ticket_id END)::FLOAT / COUNT(DISTINCT cm.ticket_id) * 100
            ELSE 0 
        END::NUMERIC, 2
    ) AS completion_percentage
FROM learning.paths p
LEFT JOIN learning.concept_metadata cm ON p.id = cm.path_id
LEFT JOIN learning.progress pr ON cm.ticket_id = pr.ticket_id AND pr.cognito_user_id = p.cognito_user_id
GROUP BY p.id, p.title, p.cognito_user_id, p.created_at, p.total_chunks;

-- View: Ticket details with learning metadata
CREATE VIEW learning.v_ticket_learning_details AS
SELECT 
    t.id AS ticket_id,
    t.summary AS ticket_summary,
    t.type AS ticket_type,
    t.status AS ticket_status,
    cm.path_id,
    cm.chunk_id,
    cm.relevance_score,
    cm.question_generated,
    COUNT(DISTINCT pre.prerequisite_ticket_id) AS prerequisite_count,
    COUNT(DISTINCT dep.concept_ticket_id) AS dependent_count
FROM public.ticket t
INNER JOIN learning.concept_metadata cm ON t.id = cm.ticket_id
LEFT JOIN learning.prerequisites pre ON t.id = pre.concept_ticket_id
LEFT JOIN learning.prerequisites dep ON t.id = dep.prerequisite_ticket_id
GROUP BY t.id, t.summary, t.type, t.status, cm.path_id, cm.chunk_id, cm.relevance_score, cm.question_generated;

-- View: Prerequisites graph (flattened)
CREATE VIEW learning.v_prerequisites_graph AS
SELECT 
    c.id AS concept_ticket_id,
    c.summary AS concept_summary,
    p.id AS prerequisite_ticket_id,
    p.summary AS prerequisite_summary,
    pr.created_at AS relationship_created
FROM learning.prerequisites pr
INNER JOIN public.ticket c ON pr.concept_ticket_id = c.id
INNER JOIN public.ticket p ON pr.prerequisite_ticket_id = p.id
ORDER BY c.id, p.id;

-- =====================================================
-- 9. Grant permissions on tables and views
-- =====================================================

-- Grant all privileges on tables to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA learning TO learntrac_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA learning TO learntrac_admin;

-- Grant usage on views
GRANT SELECT ON ALL TABLES IN SCHEMA learning TO learntrac_admin;

-- =====================================================
-- 10. Create helper functions
-- =====================================================

-- Function to check circular dependencies in prerequisites
CREATE OR REPLACE FUNCTION learning.check_circular_dependency(
    p_concept_id INTEGER,
    p_prerequisite_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    has_circular BOOLEAN;
BEGIN
    -- Check if adding this prerequisite would create a circular dependency
    WITH RECURSIVE prereq_chain AS (
        -- Start with the proposed prerequisite
        SELECT prerequisite_ticket_id, concept_ticket_id
        FROM learning.prerequisites
        WHERE concept_ticket_id = p_prerequisite_id
        
        UNION
        
        -- Recursively find all prerequisites of prerequisites
        SELECT p.prerequisite_ticket_id, p.concept_ticket_id
        FROM learning.prerequisites p
        INNER JOIN prereq_chain pc ON p.concept_ticket_id = pc.prerequisite_ticket_id
    )
    SELECT EXISTS (
        SELECT 1 FROM prereq_chain WHERE prerequisite_ticket_id = p_concept_id
    ) INTO has_circular;
    
    RETURN has_circular;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION learning.check_circular_dependency IS 'Checks if adding a prerequisite would create a circular dependency';

-- =====================================================
-- End transaction
-- =====================================================
COMMIT;

-- =====================================================
-- Verification queries (run these after creation)
-- =====================================================
-- SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'learning';
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'learning' ORDER BY table_name;
-- SELECT count(*) FROM information_schema.table_constraints WHERE table_schema = 'learning' AND constraint_type = 'FOREIGN KEY';