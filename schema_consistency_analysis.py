#!/usr/bin/env python3
"""
Schema Consistency Analysis for LearnTrac Learning Path System

This script analyzes schema consistency between:
1. Learning ticket UI requirements (from Trac macros and custom fields)
2. RDS PostgreSQL database schema
3. API output data structures

Identifies mismatches and provides recommendations for alignment.
"""

import asyncio
import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """Analyzes schema consistency across UI, Database, and API"""
    
    def __init__(self):
        self.db_connection = None
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "ui_requirements": {},
            "database_schema": {},
            "api_structures": {},
            "mismatches": [],
            "recommendations": []
        }
    
    async def connect_to_database(self):
        """Connect to RDS PostgreSQL database"""
        try:
            # Using the connection string from database.py
            self.db_connection = await asyncpg.connect(
                host="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com",
                port=5432,
                user="learntrac_admin", 
                password="Vp-Sl}}D[(j&zxP5cjh%MTQtitYq2ic7",
                database="learntrac",
                ssl="require"
            )
            logger.info("Connected to RDS PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    async def analyze_ui_requirements(self):
        """Analyze UI schema requirements from Trac macros and expected fields"""
        
        # From the learning path macro analysis - UI expects these data structures
        ui_requirements = {
            "learning_path_display": {
                "path_id": "string (UUID)",
                "title": "string", 
                "description": "string",
                "difficulty_level": "string (beginner|intermediate|advanced)",
                "total_concepts": "integer",
                "completed_concepts": "integer",
                "completion_percentage": "float",
                "created_at": "timestamp",
                "user_info": {
                    "cognito_username": "string",
                    "cognito_email": "string", 
                    "cognito_name": "string",
                    "cognito_groups": "array"
                }
            },
            "ticket_details": {
                "ticket_id": "integer",
                "summary": "string",
                "description": "string", 
                "status": "string",
                "custom_fields": {
                    "question": "text",
                    "expected_answer": "text",
                    "question_difficulty": "integer (1-5)",
                    "question_context": "text",
                    "chunk_id": "string",
                    "cognito_user_id": "string",
                    "relevance_score": "float (0-1)",
                    "learning_type": "string",
                    "auto_generated": "boolean",
                    "metadata_*": "dynamic fields from chunk metadata"
                },
                "learning_metadata": {
                    "concept_id": "UUID",
                    "path_id": "UUID", 
                    "sequence_order": "integer",
                    "concept_type": "string",
                    "difficulty_score": "float",
                    "mastery_threshold": "float",
                    "estimated_minutes": "integer",
                    "tags": "array",
                    "resources": "jsonb"
                },
                "prerequisites": [
                    {
                        "prereq_ticket_id": "integer",
                        "prereq_summary": "string", 
                        "requirement_type": "string"
                    }
                ],
                "progress": {
                    "status": "string (not_started|in_progress|completed|mastered)",
                    "mastery_score": "float (0-1)",
                    "time_spent_minutes": "integer", 
                    "attempt_count": "integer",
                    "last_accessed": "timestamp",
                    "completed_at": "timestamp",
                    "notes": "text"
                }
            }
        }
        
        self.analysis_results["ui_requirements"] = ui_requirements
        logger.info("Analyzed UI requirements")
    
    async def analyze_database_schema(self):
        """Analyze actual database schema structure"""
        
        if not self.db_connection:
            logger.error("No database connection available")
            return
        
        schema_info = {}
        
        try:
            # Get learning schema tables
            tables = await self.db_connection.fetch("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'learning'
                ORDER BY table_name
            """)
            
            schema_info["learning_tables"] = [dict(row) for row in tables]
            
            # Get detailed column information for each table
            for table in tables:
                table_name = table['table_name']
                columns = await self.db_connection.fetch("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns 
                    WHERE table_schema = 'learning' AND table_name = $1
                    ORDER BY ordinal_position
                """, table_name)
                
                schema_info[f"learning.{table_name}_columns"] = [dict(row) for row in columns]
            
            # Get foreign key constraints
            fk_constraints = await self.db_connection.fetch("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_schema = 'learning'
                ORDER BY tc.table_name, kcu.column_name
            """)
            
            schema_info["foreign_keys"] = [dict(row) for row in fk_constraints]
            
            # Check if tables actually exist (detect schema mismatches)
            table_existence = {}
            expected_tables = [
                'learning_paths', 'paths', 
                'concept_metadata', 'concept_meta',
                'prerequisites', 'prereqs',
                'progress', 'learning_progress'
            ]
            
            for table in expected_tables:
                exists = await self.db_connection.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'learning' AND table_name = $1
                    )
                """, table)
                table_existence[table] = exists
            
            schema_info["table_existence_check"] = table_existence
            
            # Check Trac ticket table structure
            trac_ticket_columns = await self.db_connection.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'ticket'
                ORDER BY ordinal_position
            """)
            
            schema_info["trac_ticket_columns"] = [dict(row) for row in trac_ticket_columns]
            
            # Check ticket_custom table
            ticket_custom_exists = await self.db_connection.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'ticket_custom'
                )
            """)
            
            schema_info["ticket_custom_exists"] = ticket_custom_exists
            
            if ticket_custom_exists:
                ticket_custom_columns = await self.db_connection.fetch("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'ticket_custom'
                    ORDER BY ordinal_position
                """)
                schema_info["ticket_custom_columns"] = [dict(row) for row in ticket_custom_columns]
            
        except Exception as e:
            logger.error(f"Database schema analysis failed: {e}")
            schema_info["error"] = str(e)
        
        self.analysis_results["database_schema"] = schema_info
        logger.info("Analyzed database schema")
    
    async def analyze_api_structures(self):
        """Analyze API data structures from ticket service"""
        
        # From the code analysis - API produces these structures
        api_structures = {
            "vector_search_to_learning_path_input": {
                "query": "string",
                "min_score": "float (0.0-1.0)",
                "max_chunks": "integer (1-50)", 
                "path_title": "string (optional)",
                "difficulty_level": "string (beginner|intermediate|advanced)"
            },
            "vector_search_chunk_format": {
                "id": "string",
                "content": "string",
                "subject": "string",
                "concept": "string", 
                "score": "float",
                "has_prerequisite": "array or null",
                "prerequisite_for": "array or null"
            },
            "transformed_chunk_format": {
                "id": "string",
                "content": "string",
                "concept": "string (with fallback to 'Unknown Concept')",
                "subject": "string (with fallback to 'General')",
                "score": "float",
                "has_prerequisite": "array or null",
                "prerequisite_for": "array or null",
                "metadata": {
                    "source": "string ('vector_search')",
                    "search_score": "float"
                }
            },
            "learning_path_response": {
                "path_id": "string (UUID)",
                "message": "string",
                "ticket_count": "integer",
                "prerequisite_count": "integer"
            },
            "database_inserts": {
                "learning_paths_table": {
                    "title": "string",
                    "description": "string (query)",
                    "difficulty_level": "string", 
                    "created_by": "string (user_id)",
                    "tags": "array"
                },
                "ticket_table": {
                    "type": "string ('learning_concept')",
                    "summary": "string (concept name)",
                    "description": "string (content)",
                    "owner": "string (user_id)",
                    "keywords": "string (formatted tags)"
                },
                "ticket_custom_table": [
                    {"name": "question", "value": "string"},
                    {"name": "expected_answer", "value": "string"},
                    {"name": "question_difficulty", "value": "string (integer)"},
                    {"name": "question_context", "value": "string"},
                    {"name": "chunk_id", "value": "string"},
                    {"name": "cognito_user_id", "value": "string"},
                    {"name": "relevance_score", "value": "string (float)"},
                    {"name": "learning_type", "value": "string"},
                    {"name": "auto_generated", "value": "string (boolean)"},
                    {"name": "metadata_*", "value": "string (dynamic)"}
                ],
                "concept_metadata_table": {
                    "concept_id": "UUID",
                    "ticket_id": "integer",
                    "path_id": "UUID",
                    "sequence_order": "integer",
                    "concept_type": "string ('lesson')",
                    "difficulty_score": "integer (3)",
                    "mastery_threshold": "float (0.8)",
                    "practice_questions": "null",
                    "learning_objectives": "null", 
                    "resources": "jsonb (chunk metadata)",
                    "estimated_minutes": "integer (30)",
                    "tags": "array (['auto-generated'])"
                },
                "prerequisites_table": {
                    "prerequisite_id": "UUID",
                    "concept_id": "UUID",
                    "prereq_concept_id": "UUID", 
                    "requirement_type": "string ('mandatory')"
                }
            },
            "ticket_details_response": {
                "ticket_id": "integer",
                "summary": "string",
                "description": "string",
                "status": "string",
                "milestone": "string",
                "created_time": "timestamp",
                "updated_time": "timestamp",
                "owner": "string",
                "reporter": "string",
                "keywords": "string",
                "concept_id": "UUID",
                "path_id": "UUID",
                "sequence_order": "integer",
                "concept_type": "string",
                "difficulty_score": "float",
                "mastery_threshold": "float",
                "estimated_minutes": "integer",
                "tags": "array",
                "resources": "jsonb",
                "progress_status": "string",
                "mastery_score": "float",
                "time_spent_minutes": "integer",
                "attempt_count": "integer",
                "last_accessed": "timestamp",
                "completed_at": "timestamp",
                "progress_notes": "string",
                "custom_fields": "jsonb",
                "prerequisites": "array"
            }
        }
        
        self.analysis_results["api_structures"] = api_structures
        logger.info("Analyzed API structures")
    
    def detect_schema_mismatches(self):
        """Detect mismatches between UI, Database, and API"""
        
        mismatches = []
        recommendations = []
        
        db_schema = self.analysis_results.get("database_schema", {})
        table_existence = db_schema.get("table_existence_check", {})
        
        # Check for missing tables
        if not table_existence.get("learning_paths") and not table_existence.get("paths"):
            mismatches.append({
                "type": "missing_table",
                "severity": "critical",
                "description": "Neither 'learning_paths' nor 'paths' table exists in learning schema",
                "impact": "API will fail when trying to insert learning path data"
            })
            recommendations.append({
                "type": "create_table", 
                "priority": "high",
                "description": "Create learning.learning_paths table matching API expectations",
                "sql_needed": True
            })
        
        # Check API vs Database column mismatches
        api_inserts = self.analysis_results.get("api_structures", {}).get("database_inserts", {})
        
        # Check learning paths table structure
        if "learning_paths_table" in api_inserts:
            api_fields = set(api_inserts["learning_paths_table"].keys())
            
            # Check if we have the table columns
            learning_tables = db_schema.get("learning_tables", [])
            table_names = [t["table_name"] for t in learning_tables]
            
            if "learning_paths" not in table_names and "paths" not in table_names:
                mismatches.append({
                    "type": "table_structure_mismatch",
                    "severity": "critical", 
                    "description": "Learning paths table missing - API expects to insert: " + ", ".join(api_fields),
                    "expected_fields": list(api_fields),
                    "actual_fields": []
                })
        
        # Check concept_metadata mismatches
        if not table_existence.get("concept_metadata"):
            mismatches.append({
                "type": "missing_table",
                "severity": "critical",
                "description": "concept_metadata table missing",
                "impact": "Cannot store learning concept metadata"
            })
        
        # Check prerequisites table
        if not table_existence.get("prerequisites"):
            mismatches.append({
                "type": "missing_table", 
                "severity": "critical",
                "description": "prerequisites table missing",
                "impact": "Cannot store prerequisite relationships"
            })
        
        # Check ticket_custom compatibility
        if not db_schema.get("ticket_custom_exists"):
            mismatches.append({
                "type": "missing_table",
                "severity": "critical",
                "description": "ticket_custom table missing",
                "impact": "Cannot store learning-specific custom fields (questions, answers, etc.)"
            })
        
        # Check for schema naming inconsistencies
        schema_variations = {
            "learning_paths vs paths": table_existence.get("learning_paths", False) or table_existence.get("paths", False),
            "concept_metadata vs concept_meta": table_existence.get("concept_metadata", False) or table_existence.get("concept_meta", False)
        }
        
        for variation, exists in schema_variations.items():
            if not exists:
                mismatches.append({
                    "type": "schema_inconsistency",
                    "severity": "high",
                    "description": f"Table naming inconsistency: {variation}",
                    "impact": "API and database schema don't align"
                })
        
        self.analysis_results["mismatches"] = mismatches
        self.analysis_results["recommendations"] = recommendations
        
        logger.info(f"Detected {len(mismatches)} schema mismatches")
    
    def generate_fix_script(self):
        """Generate SQL script to fix schema mismatches"""
        
        fix_script = """-- Schema Fix Script for LearnTrac Learning Path System
-- Generated: {timestamp}
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
    resources JSONB DEFAULT '{{}}'::jsonb,
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
        '{{}}'::json
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
""".format(timestamp=self.analysis_results["timestamp"])
        
        return fix_script
    
    async def run_analysis(self):
        """Run complete schema consistency analysis"""
        
        logger.info("Starting schema consistency analysis...")
        
        # Connect to database
        if not await self.connect_to_database():
            logger.error("Cannot proceed without database connection")
            return False
        
        try:
            # Run all analysis steps
            await self.analyze_ui_requirements()
            await self.analyze_database_schema()
            await self.analyze_api_structures()
            
            # Detect mismatches
            self.detect_schema_mismatches()
            
            # Generate reports
            self.save_analysis_results()
            fix_script = self.generate_fix_script()
            self.save_fix_script(fix_script)
            
            # Summary
            self.print_summary()
            
            return True
            
        finally:
            if self.db_connection:
                await self.db_connection.close()
                logger.info("Database connection closed")
    
    def save_analysis_results(self):
        """Save analysis results to JSON file"""
        
        filename = f"schema_consistency_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        logger.info(f"Analysis results saved to {filename}")
    
    def save_fix_script(self, fix_script: str):
        """Save SQL fix script to file"""
        
        filename = f"schema_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, 'w') as f:
            f.write(fix_script)
        
        logger.info(f"Fix script saved to {filename}")
    
    def print_summary(self):
        """Print analysis summary"""
        
        print("\n" + "="*80)
        print("SCHEMA CONSISTENCY ANALYSIS SUMMARY")
        print("="*80)
        
        mismatches = self.analysis_results.get("mismatches", [])
        recommendations = self.analysis_results.get("recommendations", [])
        
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"   - Total mismatches found: {len(mismatches)}")
        print(f"   - Critical issues: {len([m for m in mismatches if m.get('severity') == 'critical'])}")
        print(f"   - High priority issues: {len([m for m in mismatches if m.get('severity') == 'high'])}")
        print(f"   - Recommendations: {len(recommendations)}")
        
        if mismatches:
            print(f"\n🚨 CRITICAL MISMATCHES:")
            for mismatch in mismatches:
                if mismatch.get('severity') == 'critical':
                    print(f"   ❌ {mismatch['description']}")
                    if 'impact' in mismatch:
                        print(f"      Impact: {mismatch['impact']}")
        
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                priority_icon = "🔴" if rec.get('priority') == 'high' else "🟡"
                print(f"   {priority_icon} {rec['description']}")
        
        # Database state summary
        db_schema = self.analysis_results.get("database_schema", {})
        learning_tables = db_schema.get("learning_tables", [])
        table_existence = db_schema.get("table_existence_check", {})
        
        print(f"\n📋 DATABASE STATE:")
        print(f"   - Learning schema tables found: {len(learning_tables)}")
        for table in learning_tables:
            print(f"     ✓ {table['table_name']} ({table['table_type']})")
        
        print(f"   - Expected table existence:")
        for table, exists in table_existence.items():
            status = "✓" if exists else "❌"
            print(f"     {status} {table}")
        
        print(f"\n🔧 NEXT STEPS:")
        if mismatches:
            print(f"   1. Review the generated schema_fix_*.sql file")
            print(f"   2. Test the fix script on a development database")
            print(f"   3. Execute the fix script on production RDS")
            print(f"   4. Re-run this analysis to verify fixes")
        else:
            print(f"   ✅ No schema mismatches detected!")
            print(f"   ✅ UI, Database, and API schemas are consistent")
        
        print(f"\n📄 Files generated:")
        print(f"   - schema_consistency_analysis_*.json (detailed results)")
        print(f"   - schema_fix_*.sql (SQL fix script)")


async def main():
    """Main function"""
    analyzer = SchemaAnalyzer()
    success = await analyzer.run_analysis()
    
    if success:
        print(f"\n✅ Schema analysis completed successfully")
    else:
        print(f"\n❌ Schema analysis failed")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))