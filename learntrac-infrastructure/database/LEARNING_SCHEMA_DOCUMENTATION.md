# Learning Schema Documentation

## Overview

The learning schema has been successfully created in the RDS PostgreSQL instance alongside the existing Trac tables. This schema provides the foundation for the LearnTrac learning path system.

## Schema Structure

### Database Details
- **Host**: hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com
- **Database**: learntrac
- **Schema**: learning
- **PostgreSQL Version**: 15.8

### Tables Created

#### 1. learning.paths
Stores learning paths created by users.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key, auto-generated |
| title | VARCHAR(255) | User-friendly title for the learning path |
| query_text | TEXT | Original query text used to generate the path |
| cognito_user_id | VARCHAR(100) | AWS Cognito user ID who created the path |
| created_at | TIMESTAMP | When the path was created |
| total_chunks | INTEGER | Total number of chunks/concepts in this path |
| question_difficulty | INTEGER | Difficulty level for generated questions (1-5) |

#### 2. learning.concept_metadata
Links Trac tickets to learning paths with metadata.

| Column | Type | Description |
|--------|------|-------------|
| ticket_id | INTEGER | Primary key, references public.ticket(id) |
| path_id | UUID | References learning.paths(id) |
| chunk_id | VARCHAR(100) | Identifier from the source knowledge base chunk |
| relevance_score | FLOAT | Relevance score from vector search (0-1) |
| question_generated | BOOLEAN | Whether a question was successfully generated |
| created_at | TIMESTAMP | When the concept was created |

#### 3. learning.prerequisites
Defines prerequisite relationships between learning concepts.

| Column | Type | Description |
|--------|------|-------------|
| concept_ticket_id | INTEGER | The ticket that has prerequisites |
| prerequisite_ticket_id | INTEGER | The ticket that is a prerequisite |
| created_at | TIMESTAMP | When the relationship was created |

**Constraint**: Tickets cannot be their own prerequisite.

#### 4. learning.progress
Tracks user progress through learning concepts.

| Column | Type | Description |
|--------|------|-------------|
| cognito_user_id | VARCHAR(100) | AWS Cognito user ID |
| ticket_id | INTEGER | The learning concept ticket |
| status | VARCHAR(20) | Current progress status (not_started, in_progress, completed, mastered) |
| started_at | TIMESTAMP | When the user started this concept |
| last_accessed | TIMESTAMP | Last time the user accessed this concept |
| completed_at | TIMESTAMP | When the user completed this concept |
| time_spent_minutes | INTEGER | Total time spent on this concept |
| notes | TEXT | User notes |
| last_answer | TEXT | User's last answer to the question |
| answer_score | FLOAT | Score from LLM evaluation (0-1) |
| answer_feedback | TEXT | Feedback from LLM evaluation |

### Views Created

#### 1. learning.v_user_path_summary
Provides a summary of user learning paths with progress statistics.

#### 2. learning.v_ticket_learning_details
Shows ticket details with learning metadata including prerequisite counts.

#### 3. learning.v_prerequisites_graph
Flattened view of prerequisite relationships for easy querying.

### Indexes

The following indexes were created for performance optimization:

- **Paths table**: cognito_user_id, created_at (DESC)
- **Concept metadata**: path_id, chunk_id
- **Prerequisites**: prerequisite_ticket_id
- **Progress**: ticket_id, cognito_user_id, status, last_accessed (DESC)

### Foreign Key Relationships

All foreign keys have CASCADE delete behavior:

1. **concept_metadata.ticket_id** → public.ticket(id)
2. **concept_metadata.path_id** → learning.paths(id)
3. **prerequisites.concept_ticket_id** → public.ticket(id)
4. **prerequisites.prerequisite_ticket_id** → public.ticket(id)
5. **progress.ticket_id** → public.ticket(id)

### Helper Functions

#### learning.check_circular_dependency(concept_id, prerequisite_id)
Checks if adding a prerequisite would create a circular dependency. Returns BOOLEAN.

## Testing Results

All foreign key relationships have been tested and verified:

- ✅ Path creation with UUID generation
- ✅ Concept metadata linking to both paths and tickets
- ✅ Prerequisite relationships between tickets
- ✅ Progress tracking for users
- ✅ CASCADE delete behavior
- ✅ All views return correct data

## Files Created

1. **create_learning_schema.sql** - Main schema creation script
2. **execute_learning_schema.sh** - Shell script to execute the SQL
3. **test_learning_schema_simple.sql** - Foreign key relationship tests
4. **test_learning_db_connection.py** - Python connection test script
5. **test_rds_connection_aws.sh** - AWS CLI connection test script

## Next Steps

1. **Integration with FastAPI Service**: The schema is ready for the Learning Service API to connect and use.
2. **Migration Script**: The existing migration script (05_learning_schema_migrate.sql) can be used if needed.
3. **Monitoring**: Set up monitoring for table growth and query performance.
4. **Backup**: Ensure the learning schema is included in RDS backup procedures.

## Security Considerations

- All user identification uses Cognito user IDs, not database users
- Foreign keys ensure referential integrity
- Check constraints validate data ranges
- Permissions are granted only to the application user (learntrac_admin)

## Performance Considerations

- Indexes are created on all foreign keys and frequently queried columns
- Views are created for complex queries to simplify application code
- UUID generation uses the pgcrypto extension for performance
- All timestamp columns use database server time for consistency