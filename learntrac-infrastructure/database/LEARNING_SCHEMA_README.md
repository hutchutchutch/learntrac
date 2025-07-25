# Learning Schema Documentation

## Overview

The Learning Schema extends the Trac database with educational tracking capabilities, enabling LearnTrac to manage learning paths, concepts, prerequisites, and user progress.

## Schema Structure

### Core Tables

1. **learning.paths**
   - Defines structured learning sequences
   - Contains path metadata, difficulty levels, and estimated completion times
   - UUID-based primary keys for distributed system compatibility

2. **learning.concept_metadata**
   - Stores information about individual learning concepts/topics
   - Includes difficulty scores, learning objectives, and time estimates
   - Supports tagging and categorization

3. **learning.prerequisites**
   - Defines relationships between concepts
   - Supports different requirement types: required, recommended, optional
   - Includes minimum mastery levels for prerequisites

4. **learning.path_concepts**
   - Junction table linking concepts to learning paths
   - Maintains sequence order within paths
   - Tracks required vs optional concepts

5. **learning.progress**
   - Tracks individual user progress through paths and concepts
   - Links to Trac's session system via user_sid
   - Stores mastery levels, time spent, and assessment scores

6. **learning.resources**
   - Links Trac tickets and wiki pages to learning concepts
   - Supports external resources
   - Identifies primary vs supplementary resources

7. **learning.activities**
   - Logs specific learning interactions and activities
   - Flexible JSONB storage for activity-specific data
   - Enables detailed analytics

## Installation

### Prerequisites

1. PostgreSQL database with Trac schema already initialized
2. UUID extension support in PostgreSQL
3. Database user with schema creation privileges

### Quick Start

```bash
# Navigate to database directory
cd learntrac-infrastructure/database/

# Run the initialization script
./initialize_learning_schema.sh
```

### Manual Installation

```bash
# Initialize the schema
psql -h $DB_HOST -d $DB_NAME -U $DB_USER -f 04_learning_schema_init.sql

# Validate the installation
psql -h $DB_HOST -d $DB_NAME -U $DB_USER -f 07_validate_learning_schema.sql
```

## SQL Scripts

- **04_learning_schema_init.sql**: Creates all tables, indexes, and relationships
- **05_learning_schema_migrate.sql**: Handles migrations and updates
- **06_learning_schema_rollback.sql**: Removes the learning schema (use with caution!)
- **07_validate_learning_schema.sql**: Validates schema structure and integrity

## Key Features

### UUID Primary Keys
All tables use UUID primary keys generated via `uuid_generate_v4()` for:
- Distributed system compatibility
- Collision-free identifiers
- Better security (non-sequential)

### JSONB Metadata
Flexible metadata storage using PostgreSQL's JSONB type for:
- Extended attributes without schema changes
- Assessment scores and activity data
- Future extensibility

### Automatic Timestamps
Update triggers maintain `updated_at` timestamps automatically.

### Performance Optimization
Comprehensive indexes on:
- Foreign key columns
- Frequently queried fields (status, user_sid, etc.)
- JSONB fields using GIN indexes
- Timestamp fields for time-based queries

## Integration with Trac

The learning schema integrates with Trac through:

1. **User Sessions**: `progress.user_sid` links to `trac.session.sid`
2. **Resources**: Links to `trac.ticket` and `trac.wiki` tables
3. **Permissions**: Uses Trac's permission system via the `learntrac_app` user

## Example Queries

### Get user's current learning path progress
```sql
SELECT 
    p.title as path_title,
    COUNT(DISTINCT pc.concept_id) as total_concepts,
    COUNT(DISTINCT pr.concept_id) FILTER (WHERE pr.status = 'completed') as completed_concepts,
    ROUND(AVG(pr.mastery_level)::numeric, 2) as avg_mastery
FROM learning.paths p
JOIN learning.path_concepts pc ON p.id = pc.path_id
LEFT JOIN learning.progress pr ON pc.concept_id = pr.concept_id 
    AND pr.user_sid = 'user123'
WHERE p.is_active = true
GROUP BY p.id, p.title;
```

### Find concepts ready to learn (prerequisites met)
```sql
WITH user_completed AS (
    SELECT concept_id 
    FROM learning.progress 
    WHERE user_sid = 'user123' 
    AND status = 'completed'
    AND mastery_level >= 0.7
)
SELECT DISTINCT c.*
FROM learning.concept_metadata c
WHERE NOT EXISTS (
    -- User hasn't completed this concept
    SELECT 1 FROM user_completed uc WHERE uc.concept_id = c.id
)
AND NOT EXISTS (
    -- All prerequisites are met
    SELECT 1 
    FROM learning.prerequisites p
    WHERE p.concept_id = c.id
    AND p.requirement_type = 'required'
    AND p.prerequisite_concept_id NOT IN (SELECT concept_id FROM user_completed)
);
```

## Maintenance

### Regular Tasks

1. **Analyze tables for query optimization**:
   ```sql
   ANALYZE learning.progress;
   ANALYZE learning.activities;
   ```

2. **Monitor table sizes**:
   ```sql
   SELECT 
       schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'learning'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

3. **Check for orphaned records**:
   ```sql
   -- Run validation script
   psql -f 07_validate_learning_schema.sql
   ```

## Security Considerations

1. **Row-Level Security**: Consider implementing RLS for multi-tenant deployments
2. **Audit Trails**: The activities table provides basic audit functionality
3. **Permissions**: Ensure `learntrac_app` user has minimal required privileges
4. **Data Privacy**: Personal progress data should be handled according to privacy policies

## Future Enhancements

Potential areas for extension:

1. **Gamification**: Add badges, achievements, and leaderboards
2. **Collaborative Learning**: Group progress tracking and peer learning
3. **Assessment Engine**: Formal testing and certification tracking
4. **Learning Analytics**: Advanced reporting and predictive modeling
5. **Content Versioning**: Track changes to learning materials over time