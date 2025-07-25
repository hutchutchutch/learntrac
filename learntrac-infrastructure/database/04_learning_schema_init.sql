-- Learning Schema Initialization Script
-- This script creates the learning namespace and all related tables
-- Target: PostgreSQL
-- Dependencies: Trac schema must be initialized first

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create learning schema
CREATE SCHEMA IF NOT EXISTS learning;

-- Set search path to include both schemas
SET search_path TO learning, trac, public;

-- Learning Paths table
-- Represents structured learning sequences
CREATE TABLE IF NOT EXISTS learning.paths (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path_code VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    estimated_hours INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Concept Metadata table
-- Stores information about learning concepts/topics
CREATE TABLE IF NOT EXISTS learning.concept_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags TEXT[],
    difficulty_score DECIMAL(3,2) CHECK (difficulty_score >= 0 AND difficulty_score <= 10),
    learning_objectives TEXT[],
    estimated_learning_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Prerequisites table
-- Defines prerequisite relationships between concepts
CREATE TABLE IF NOT EXISTS learning.prerequisites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL,
    prerequisite_concept_id UUID NOT NULL,
    requirement_type VARCHAR(20) DEFAULT 'required' CHECK (requirement_type IN ('required', 'recommended', 'optional')),
    minimum_mastery_level DECIMAL(3,2) DEFAULT 0.7 CHECK (minimum_mastery_level >= 0 AND minimum_mastery_level <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE,
    UNIQUE(concept_id, prerequisite_concept_id)
);

-- Path Concepts junction table
-- Links concepts to learning paths
CREATE TABLE IF NOT EXISTS learning.path_concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    path_id UUID NOT NULL,
    concept_id UUID NOT NULL,
    sequence_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (path_id) REFERENCES learning.paths(id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE,
    UNIQUE(path_id, concept_id),
    UNIQUE(path_id, sequence_order)
);

-- Progress table
-- Tracks user progress through learning paths and concepts
CREATE TABLE IF NOT EXISTS learning.progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sid TEXT NOT NULL, -- Links to trac.session.sid
    path_id UUID,
    concept_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
    mastery_level DECIMAL(3,2) DEFAULT 0 CHECK (mastery_level >= 0 AND mastery_level <= 1),
    time_spent_minutes INTEGER DEFAULT 0,
    completion_date TIMESTAMP WITH TIME ZONE,
    last_activity_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assessment_scores JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (path_id) REFERENCES learning.paths(id) ON DELETE SET NULL,
    FOREIGN KEY (concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE,
    UNIQUE(user_sid, concept_id)
);

-- Learning Resources table
-- Links Trac tickets/wiki pages to learning concepts
CREATE TABLE IF NOT EXISTS learning.resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL,
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('ticket', 'wiki', 'external')),
    resource_id TEXT NOT NULL, -- For tickets: ticket.id::text, for wiki: wiki.name
    title VARCHAR(255),
    description TEXT,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE
);

-- Learning Activities table
-- Tracks specific learning activities and interactions
CREATE TABLE IF NOT EXISTS learning.activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_sid TEXT NOT NULL,
    concept_id UUID NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB DEFAULT '{}'::jsonb,
    duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (concept_id) REFERENCES learning.concept_metadata(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_paths_path_code ON learning.paths(path_code);
CREATE INDEX IF NOT EXISTS idx_paths_is_active ON learning.paths(is_active);
CREATE INDEX IF NOT EXISTS idx_concept_metadata_concept_code ON learning.concept_metadata(concept_code);
CREATE INDEX IF NOT EXISTS idx_concept_metadata_category ON learning.concept_metadata(category);
CREATE INDEX IF NOT EXISTS idx_concept_metadata_tags ON learning.concept_metadata USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_prerequisites_concept_id ON learning.prerequisites(concept_id);
CREATE INDEX IF NOT EXISTS idx_prerequisites_prerequisite_concept_id ON learning.prerequisites(prerequisite_concept_id);
CREATE INDEX IF NOT EXISTS idx_path_concepts_path_id ON learning.path_concepts(path_id);
CREATE INDEX IF NOT EXISTS idx_path_concepts_concept_id ON learning.path_concepts(concept_id);
CREATE INDEX IF NOT EXISTS idx_progress_user_sid ON learning.progress(user_sid);
CREATE INDEX IF NOT EXISTS idx_progress_path_id ON learning.progress(path_id);
CREATE INDEX IF NOT EXISTS idx_progress_concept_id ON learning.progress(concept_id);
CREATE INDEX IF NOT EXISTS idx_progress_status ON learning.progress(status);
CREATE INDEX IF NOT EXISTS idx_progress_last_activity ON learning.progress(last_activity_date);
CREATE INDEX IF NOT EXISTS idx_resources_concept_id ON learning.resources(concept_id);
CREATE INDEX IF NOT EXISTS idx_resources_type_id ON learning.resources(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_activities_user_sid ON learning.activities(user_sid);
CREATE INDEX IF NOT EXISTS idx_activities_concept_id ON learning.activities(concept_id);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON learning.activities(created_at);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION learning.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_paths_updated_at BEFORE UPDATE ON learning.paths
    FOR EACH ROW EXECUTE FUNCTION learning.update_updated_at_column();

CREATE TRIGGER update_concept_metadata_updated_at BEFORE UPDATE ON learning.concept_metadata
    FOR EACH ROW EXECUTE FUNCTION learning.update_updated_at_column();

CREATE TRIGGER update_progress_updated_at BEFORE UPDATE ON learning.progress
    FOR EACH ROW EXECUTE FUNCTION learning.update_updated_at_column();

-- Grant permissions to application user
-- Note: Replace 'learntrac_app' with your actual application database user
GRANT USAGE ON SCHEMA learning TO learntrac_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA learning TO learntrac_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA learning TO learntrac_app;

-- Add comments for documentation
COMMENT ON SCHEMA learning IS 'Learning management schema for tracking educational paths and progress';
COMMENT ON TABLE learning.paths IS 'Defines structured learning sequences';
COMMENT ON TABLE learning.concept_metadata IS 'Stores information about learning concepts and topics';
COMMENT ON TABLE learning.prerequisites IS 'Defines prerequisite relationships between concepts';
COMMENT ON TABLE learning.path_concepts IS 'Junction table linking concepts to learning paths';
COMMENT ON TABLE learning.progress IS 'Tracks user progress through learning paths and concepts';
COMMENT ON TABLE learning.resources IS 'Links Trac tickets and wiki pages to learning concepts';
COMMENT ON TABLE learning.activities IS 'Tracks specific learning activities and interactions';