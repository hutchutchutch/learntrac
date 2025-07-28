-- Schema Fix Script for LearnTrac Learning Path System
-- Generated: 2025-07-27T20:02:34.761832
-- Fixes schema mismatches between UI, API, and Database

BEGIN;

-- Ensure learning schema exists
CREATE SCHEMA IF NOT EXISTS learning;

-- Create learning_paths table (matching API expectations)
CREATE TABLE IF NOT EXISTS learning.learning_paths (
    path_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[]
);

-- Create concept_metadata table (matching API expectations)  
CREATE TABLE IF NOT EXISTS learning.concept_metadata (
    concept_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id INTEGER NOT NULL REFERENCES public.ticket(id) ON DELETE CASCADE,
    path_id UUID NOT NULL REFERENCES learning.learning_paths(path_id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL,
    concept_type VARCHAR(50) DEFAULT 'lesson',
    difficulty_score FLOAT DEFAULT 3.0,
    mastery_threshold FLOAT DEFAULT 0.8,
    practice_questions JSONB,
    learning_objectives JSONB,
    resources JSONB DEFAULT '{}'::jsonb,
    estimated_minutes INTEGER DEFAULT 30,
    tags TEXT[] DEFAULT ARRAY['auto-generated']::TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create prerequisites table (matching API expectations)
CREATE TABLE IF NOT EXISTS learning.prerequisites (
    prerequisite_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES learning.concept_metadata(concept_id) ON DELETE CASCADE,
    prereq_concept_id UUID NOT NULL REFERENCES learning.concept_metadata(concept_id) ON DELETE CASCADE,
    requirement_type VARCHAR(20) DEFAULT 'mandatory',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT no_self_prerequisite CHECK (concept_id != prereq_concept_id)
);

-- Create progress table (matching UI expectations)
CREATE TABLE IF NOT EXISTS learning.progress (
    student_id VARCHAR(100) NOT NULL,
    concept_id UUID NOT NULL REFERENCES learning.concept_metadata(concept_id) ON DELETE CASCADE,
    ticket_id INTEGER NOT NULL REFERENCES public.ticket(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'mastered')),
    mastery_score FLOAT CHECK (mastery_score >= 0 AND mastery_score <= 1),
    time_spent_minutes INTEGER DEFAULT 0,
    attempt_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, concept_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_learning_paths_created_by ON learning.learning_paths(created_by);
CREATE INDEX IF NOT EXISTS idx_learning_paths_created_at ON learning.learning_paths(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_concept_metadata_ticket_id ON learning.concept_metadata(ticket_id);
CREATE INDEX IF NOT EXISTS idx_concept_metadata_path_id ON learning.concept_metadata(path_id);
CREATE INDEX IF NOT EXISTS idx_concept_metadata_sequence ON learning.concept_metadata(path_id, sequence_order);

CREATE INDEX IF NOT EXISTS idx_prerequisites_concept_id ON learning.prerequisites(concept_id);
CREATE INDEX IF NOT EXISTS idx_prerequisites_prereq_concept_id ON learning.prerequisites(prereq_concept_id);

CREATE INDEX IF NOT EXISTS idx_progress_student_id ON learning.progress(student_id);
CREATE INDEX IF NOT EXISTS idx_progress_ticket_id ON learning.progress(ticket_id);
CREATE INDEX IF NOT EXISTS idx_progress_status ON learning.progress(status);

-- Ensure ticket_custom table exists for Trac integration
CREATE TABLE IF NOT EXISTS public.ticket_custom (
    ticket INTEGER NOT NULL REFERENCES public.ticket(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    value TEXT,
    PRIMARY KEY (ticket, name)
);

CREATE INDEX IF NOT EXISTS idx_ticket_custom_ticket ON public.ticket_custom(ticket);
CREATE INDEX IF NOT EXISTS idx_ticket_custom_name ON public.ticket_custom(name);

-- Create helpful views for UI integration
CREATE OR REPLACE VIEW learning.v_learning_path_summary AS
SELECT 
    lp.path_id,
    lp.title,
    lp.description,
    lp.difficulty_level,
    lp.created_by,
    lp.created_at,
    COUNT(DISTINCT cm.concept_id) AS total_concepts,
    COUNT(DISTINCT CASE WHEN p.status IN ('completed', 'mastered') THEN p.concept_id END) AS completed_concepts,
    ROUND(
        CASE 
            WHEN COUNT(DISTINCT cm.concept_id) > 0 
            THEN COUNT(DISTINCT CASE WHEN p.status IN ('completed', 'mastered') THEN p.concept_id END)::FLOAT / COUNT(DISTINCT cm.concept_id) * 100
            ELSE 0 
        END::NUMERIC, 2
    ) AS completion_percentage
FROM learning.learning_paths lp
LEFT JOIN learning.concept_metadata cm ON lp.path_id = cm.path_id
LEFT JOIN learning.progress p ON cm.concept_id = p.concept_id AND p.student_id = lp.created_by
GROUP BY lp.path_id, lp.title, lp.description, lp.difficulty_level, lp.created_by, lp.created_at;

CREATE OR REPLACE VIEW learning.v_ticket_learning_details AS
SELECT 
    t.id AS ticket_id,
    t.summary,
    t.description,
    t.status AS ticket_status,
    t.milestone,
    t.time AS created_time,
    t.changetime AS updated_time,
    t.owner,
    t.reporter,
    t.keywords,
    cm.concept_id,
    cm.path_id,
    cm.sequence_order,
    cm.concept_type,
    cm.difficulty_score,
    cm.mastery_threshold,
    cm.estimated_minutes,
    cm.tags,
    cm.resources,
    p.status AS progress_status,
    p.mastery_score,
    p.time_spent_minutes,
    p.attempt_count,
    p.last_accessed,
    p.completed_at,
    p.notes AS progress_notes,
    -- Custom fields as JSON object
    COALESCE(
        json_object_agg(tc.name, tc.value) FILTER (WHERE tc.name IS NOT NULL),
        '{}'::json
    ) AS custom_fields
FROM public.ticket t
INNER JOIN learning.concept_metadata cm ON t.id = cm.ticket_id
LEFT JOIN learning.progress p ON cm.concept_id = p.concept_id
LEFT JOIN public.ticket_custom tc ON t.id = tc.ticket
GROUP BY 
    t.id, t.summary, t.description, t.status, t.milestone, t.time, t.changetime,
    t.owner, t.reporter, t.keywords, cm.concept_id, cm.path_id, cm.sequence_order,
    cm.concept_type, cm.difficulty_score, cm.mastery_threshold, cm.estimated_minutes,
    cm.tags, cm.resources, p.status, p.mastery_score, p.time_spent_minutes,
    p.attempt_count, p.last_accessed, p.completed_at, p.notes;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA learning TO learntrac_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA learning TO learntrac_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA learning TO learntrac_admin;

COMMIT;

-- Verification queries (run after script execution)
-- SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'learning';
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'learning' ORDER BY table_name;
-- SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'learning' AND constraint_type = 'FOREIGN KEY';
