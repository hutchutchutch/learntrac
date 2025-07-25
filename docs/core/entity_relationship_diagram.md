 Entity Relationship Diagram - Question-Based Learning MVP for Trac 1.4.4
1. Overview
This document shows the entity relationships for the question-based learning MVP deployed on AWS infrastructure. We use AWS RDS PostgreSQL for all persistent data (both Trac and learning schemas), Neo4j Aura for academic content with vector embeddings, and AWS ElastiCache for caching. User authentication is handled by AWS Cognito.
2. System Data Stores
2.1 Data Store Architecture
mermaidgraph TB
    subgraph "AWS Cognito"
        COGNITO[User Pool<br/>Authentication & JWT]
    end
    
    subgraph "Neo4j Aura (External)"
        NEO[Academic Chunks<br/>with Vector Embeddings<br/>Read-Only Access]
    end
    
    subgraph "AWS RDS PostgreSQL"
        subgraph "public schema"
            TRAC[Trac Core Tables<br/>Created Fresh]
        end
        subgraph "learning schema"
            LEARN[Learning Tables<br/>Progress & Metadata]
        end
    end
    
    subgraph "AWS ElastiCache"
        CACHE[Redis Cluster<br/>Search Results: 1hr<br/>Progress: 15min<br/>Graphs: On-demand]
    end
    
    COGNITO --> TRAC
    COGNITO --> LEARN
    NEO --> CACHE
    CACHE --> LEARN
    TRAC <--> LEARN
3. AWS Cognito User Structure
3.1 Cognito User Attributes
Cognito User Pool
=================
Standard Attributes:
- sub                    # Unique user ID (UUID)
- email                  # User email (required, unique)
- email_verified         # Boolean
- name                   # Display name (required)
- updated_at            # Last modified timestamp

Custom Attributes:
- custom:role           # 'student', 'instructor', 'admin'
- custom:created_at     # Registration date
- custom:last_login     # Last authentication

Groups:
- Students              # Default group
- Instructors          # Can create content
- Administrators       # Full access
4. Neo4j Aura Chunk Structure (External Service)
4.1 Chunk Node Properties
Neo4j Chunk Node (Read-Only)
=============================
{
  id: "chunk_12345",              // Unique identifier
  content: "Text content...",     // 100-500 words of academic content
  subject: "Machine Learning",    // Broad topic (becomes milestone)
  concept: "Neural Networks",     // Specific concept
  has_prerequisite: "Perceptrons", // Previous concept (nullable)
  prerequisite_for: "Deep Learning", // Next concept (nullable)
  embedding: [0.1, 0.2, ...],     // 1536-dimension vector
  created_at: "2024-01-01",       // Timestamp
 source: "textbook_ml_ch5",      // Source reference
 difficulty_level: 3             // 1-5 scale
}

Vector Index:
- Name: chunk_embeddings
- Dimensions: 1536
- Similarity: cosine
- Min relevance: 0.65
5. AWS RDS PostgreSQL Tables
5.1 Trac Core Tables (public schema)
mermaiderDiagram
    ticket {
        INTEGER id PK "Auto-increment ID"
        TEXT type "learning_concept"
        INTEGER time "Creation timestamp"
        INTEGER changetime "Last modified"
        TEXT component "Not used"
        TEXT severity "Not used"
        TEXT priority "Normal for all"
        TEXT owner "Cognito sub"
        TEXT reporter "learning-system"
        TEXT cc "Not used"
        TEXT version "Not used"
        TEXT milestone FK "Subject from chunk"
        TEXT status "new/assigned/closed"
        TEXT resolution "fixed when mastered"
        TEXT summary "Concept from chunk"
        TEXT description "Content from chunk"
        TEXT keywords "Not used"
    }
    
    milestone {
        TEXT name PK "Subject name"
        INTEGER due "Not used"
        INTEGER completed "Not used"
        TEXT description "Subject description"
    }
    
    ticket_custom {
        INTEGER ticket PK,FK "References ticket"
        TEXT name PK "Field name"
        TEXT value "Field value"
    }
    
    session {
        TEXT sid PK "Session ID"
        INTEGER authenticated "1 if logged in"
        INTEGER last_visit "Last activity"
    }
    
    session_attribute {
        TEXT sid PK,FK "Session ID"
        TEXT name PK "Attribute name"
        TEXT value "Attribute value"
    }
    
    ticket ||--o{ ticket_custom : "has fields"
    ticket }o--|| milestone : "belongs to"
    session ||--o{ session_attribute : "has attributes"
5.2 Custom Fields for Learning (ticket_custom)
sql-- Learning-specific fields stored as rows
question                 -- Generated question text (100-500 chars)
question_difficulty      -- Difficulty level (1-5)
question_context        -- Original learning query
expected_answer         -- LLM-generated answer (200-1000 chars)
has_prerequisite        -- Concept that must be learned first
prerequisite_for        -- Concept that follows this one
chunk_id               -- Reference to Neo4j chunk
cognito_user_id        -- User who created the path
5.3 Learning Schema Tables
mermaiderDiagram
    paths {
        UUID id PK "Path identifier"
        VARCHAR title "Generated title"
        TEXT query_text "User's query"
        VARCHAR cognito_user_id FK "From Cognito sub"
        TIMESTAMP created_at "Creation time"
        INTEGER total_chunks "Found in Neo4j"
        INTEGER question_difficulty "Default 1-5"
    }
    
    concept_metadata {
        INTEGER ticket_id PK,FK "References ticket.id"
        UUID path_id FK "References paths.id"
        VARCHAR chunk_id "Neo4j chunk ID"
        FLOAT relevance_score "Vector similarity"
        BOOLEAN question_generated "Always true"
        TIMESTAMP created_at "Creation time"
    }
    
    prerequisites {
        INTEGER concept_ticket_id PK,FK "Concept"
        INTEGER prerequisite_ticket_id PK,FK "Required first"
        TIMESTAMP created_at "Link creation"
    }
    
    progress {
        VARCHAR cognito_user_id PK,FK "From Cognito"
        INTEGER ticket_id PK,FK "Concept ticket"
        VARCHAR status "not_started/studying/mastered"
        TIMESTAMP started_at "First attempt"
        TIMESTAMP last_accessed "Last activity"
        TIMESTAMP completed_at "When mastered"
        INTEGER time_spent_minutes "Total time"
        TEXT notes "User notes"
        TEXT last_answer "Recent answer"
        FLOAT answer_score "LLM score 0-1"
        TEXT answer_feedback "LLM feedback"
    }
    
    cognito_sessions {
        VARCHAR cognito_sub PK "User ID"
        VARCHAR access_token "Current token"
        VARCHAR refresh_token "For renewal"
        TIMESTAMP token_expires "Access expiry"
        VARCHAR trac_session_id FK "Links to session.sid"
        TIMESTAMP last_activity "Last request"
    }
    
    paths ||--o{ concept_metadata : "contains"
    concept_metadata ||--|| ticket : "describes"
    prerequisites }o--|| ticket : "concept"
    prerequisites }o--|| ticket : "prerequisite"
    progress }o--|| ticket : "tracks"
    cognito_sessions ||--|| session : "maps to"
6. Entity Relationships Across Systems
6.1 Cross-System Data Flow
mermaidflowchart TD
    subgraph "AWS Cognito"
        USER[User Attributes]
    end
    
    subgraph "Neo4j Aura"
        CHUNK[Chunk Nodes]
    end
    
    subgraph "AWS ElastiCache"
        SEARCH[Cached Searches]
        PROG_CACHE[Progress Cache]
        GRAPH[Graph Cache]
    end
    
    subgraph "AWS RDS - public"
        TICKET[ticket]
        CUSTOM[ticket_custom]
        MILESTONE[milestone]
        SESSION[session + attributes]
    end
    
    subgraph "AWS RDS - learning"
        PATH[paths]
        META[concept_metadata]
        PREREQ[prerequisites]
        PROGRESS[progress]
        COGN_SESS[cognito_sessions]
    end
    
    USER -->|JWT sub| COGN_SESS
    COGN_SESS -->|session_id| SESSION
    CHUNK -->|search results| SEARCH
    SEARCH -->|chunk data| META
    META -->|ticket_id| TICKET
    TICKET -->|ticket| CUSTOM
    TICKET -->|milestone| MILESTONE
    PREREQ -->|both FKs| TICKET
    PROGRESS -->|cognito_user_id| USER
    PROGRESS -->|ticket_id| TICKET
    PATH -->|cognito_user_id| USER
    PROGRESS --> PROG_CACHE
    TICKET --> GRAPH
6.2 Key Relationships
Authentication Flow:
- Cognito User ←→ cognito_sessions ←→ Trac session
- JWT token 'sub' used as primary user identifier

Data Ownership:
- paths : concept_metadata = 1:N (one path has many concepts)
- ticket : concept_metadata = 1:1 (one ticket per concept)
- cognito_user : paths = 1:N (user creates many paths)
- cognito_user : progress = 1:N (user has progress on many concepts)

Learning Flow:
- Neo4j chunks → ElastiCache → RDS tickets
- ticket : prerequisites = N:M (many-to-many via junction)
- milestone : ticket = 1:N (subjects contain concepts)
7. Database Constraints and Indexes
7.1 Primary Keys and Foreign Keys
sql-- RDS PostgreSQL Constraints

-- Learning schema primary keys
ALTER TABLE learning.paths 
    ADD PRIMARY KEY (id);

ALTER TABLE learning.concept_metadata 
    ADD PRIMARY KEY (ticket_id),
    ADD FOREIGN KEY (path_id) REFERENCES learning.paths(id),
    ADD FOREIGN KEY (ticket_id) REFERENCES public.ticket(id);

ALTER TABLE learning.prerequisites 
    ADD PRIMARY KEY (concept_ticket_id, prerequisite_ticket_id),
    ADD FOREIGN KEY (concept_ticket_id) REFERENCES public.ticket(id),
    ADD FOREIGN KEY (prerequisite_ticket_id) REFERENCES public.ticket(id);

ALTER TABLE learning.progress 
    ADD PRIMARY KEY (cognito_user_id, ticket_id),
    ADD FOREIGN KEY (ticket_id) REFERENCES public.ticket(id);

ALTER TABLE learning.cognito_sessions
    ADD PRIMARY KEY (cognito_sub),
    ADD FOREIGN KEY (trac_session_id) REFERENCES public.session(sid);
7.2 Check Constraints
sql-- Data integrity constraints
ALTER TABLE learning.progress 
    ADD CONSTRAINT chk_status 
    CHECK (status IN ('not_started', 'studying', 'mastered'));

ALTER TABLE learning.progress 
    ADD CONSTRAINT chk_score 
    CHECK (answer_score >= 0 AND answer_score <= 1);

ALTER TABLE learning.paths 
    ADD CONSTRAINT chk_difficulty 
    CHECK (question_difficulty BETWEEN 1 AND 5);

ALTER TABLE learning.prerequisites 
    ADD CONSTRAINT chk_no_self 
    CHECK (concept_ticket_id != prerequisite_ticket_id);

ALTER TABLE learning.cognito_sessions
    ADD CONSTRAINT chk_token_expires
    CHECK (token_expires > last_activity);
7.3 Performance Indexes
sql-- Trac table indexes (standard)
CREATE INDEX idx_ticket_type ON public.ticket(type);
CREATE INDEX idx_ticket_milestone ON public.ticket(milestone);
CREATE INDEX idx_ticket_status ON public.ticket(status);
CREATE INDEX idx_ticket_owner ON public.ticket(owner);
CREATE INDEX idx_ticket_custom_name ON public.ticket_custom(name);

-- Learning schema indexes
CREATE INDEX idx_paths_user ON learning.paths(cognito_user_id);
CREATE INDEX idx_concept_metadata_path ON learning.concept_metadata(path_id);
CREATE INDEX idx_concept_metadata_chunk ON learning.concept_metadata(chunk_id);
CREATE INDEX idx_prerequisites_concept ON learning.prerequisites(concept_ticket_id);
CREATE INDEX idx_prerequisites_prereq ON learning.prerequisites(prerequisite_ticket_id);
CREATE INDEX idx_progress_user ON learning.progress(cognito_user_id);
CREATE INDEX idx_progress_status ON learning.progress(status);
CREATE INDEX idx_progress_score ON learning.progress(answer_score);
CREATE INDEX idx_cognito_sessions_trac ON learning.cognito_sessions(trac_session_id);
CREATE INDEX idx_cognito_sessions_expires ON learning.cognito_sessions(token_expires);
8. ElastiCache Key Structure
8.1 Cache Key Patterns
yamlSearch Results:
  Pattern: "search:{query_hash}:{cognito_sub}"
  TTL: 3600 seconds (1 hour)
  Value: JSON array of chunks

User Progress:
  Pattern: "progress:{cognito_sub}:{ticket_id}"
  TTL: 900 seconds (15 minutes)
  Value: JSON with status, score, feedback

Knowledge Graphs:
  Pattern: "graph:{milestone}:{cognito_sub}"
  TTL: Until invalidated by progress change
  Value: Base64 encoded PNG + image map

Session Data:
  Pattern: "session:{cognito_sub}"
  TTL: 7200 seconds (2 hours)
  Value: JSON with preferences, current path

API Responses:
  Pattern: "api:{endpoint}:{params_hash}:{cognito_sub}"
  TTL: 300 seconds (5 minutes)
  Value: Cached API response
9. Data Volume Estimates
9.1 Storage Requirements
yamlPer Learning Path:
  Neo4j Aura: 
    - 20 chunks × 2KB = 40KB (already stored)
  
  RDS PostgreSQL:
    - 1 path record: 0.5KB
    - 20 tickets: 20KB
    - 120 custom fields (6 per ticket): 24KB
    - 20 metadata records: 2KB
    - ~10 prerequisites: 0.5KB
    Total: ~47KB per path

Per User Progress:
  - 20 progress records: 10KB
  - Answer attempts: ~20KB
  - Session data: 2KB
  Total: ~32KB per user per path

ElastiCache Usage:
  - Search cache: 40KB per unique search
  - Progress cache: 1KB per concept
  - Graph cache: 100KB per graph
  - Session cache: 5KB per user
9.2 Query Performance Targets
yamlAuthentication:
  - Cognito JWT validation: <50ms
  - Session lookup: <10ms

Search Operations:
  - ElastiCache hit: <10ms
  - Neo4j Aura vector search: 1-2 seconds
  - Results caching: <50ms

Database Operations:
  - Ticket creation batch (20): 2-3 seconds
  - Progress query (indexed): <50ms
  - Graph data query: <200ms

API Gateway:
  - Request routing: <30ms
  - Authorization: <50ms
  - Total overhead: <100ms
10. Data Integrity and Security
10.1 Security Rules
yamlRow-Level Security:
  - Users can only see their own progress
  - Cognito sub used for all queries
  - No cross-user data access

API Security:
  - All requests require valid JWT
  - User context extracted from token
  - Database queries parameterized

Data Encryption:
  - RDS: Encryption at rest (AES-256)
  - ElastiCache: In-transit encryption
  - Neo4j Aura: TLS connection
  - Cognito: Tokens signed with RS256
10.2 Audit Trail
sql-- Audit columns on all learning tables
ALTER TABLE learning.paths ADD COLUMN created_by VARCHAR(100) DEFAULT current_user;
ALTER TABLE learning.progress ADD COLUMN updated_by VARCHAR(100) DEFAULT current_user;
ALTER TABLE learning.progress ADD COLUMN update_count INTEGER DEFAULT 0;

-- Trigger to track updates
CREATE OR REPLACE FUNCTION update_audit_fields()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_by = current_user;
    NEW.update_count = OLD.update_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER progress_audit_trigger
BEFORE UPDATE ON learning.progress
FOR EACH ROW EXECUTE FUNCTION update_audit_fields();
11. Views for Application Access
11.1 User Progress View
sqlCREATE VIEW learning.user_progress_view AS
SELECT 
    p.cognito_user_id,
    t.id as ticket_id,
    t.summary as concept,
    t.milestone as subject,
    tc_q.value as question,
    tc_d.value as difficulty,
    p.status,
    p.answer_score,
    p.last_answer,
    p.answer_feedback,
    p.time_spent_minutes,
    p.last_accessed
FROM learning.progress p
JOIN public.ticket t ON p.ticket_id = t.id
LEFT JOIN public.ticket_custom tc_q ON t.id = tc_q.ticket 
    AND tc_q.name = 'question'
LEFT JOIN public.ticket_custom tc_d ON t.id = tc_d.ticket 
    AND tc_d.name = 'question_difficulty'
WHERE t.type = 'learning_concept';

-- Grant access
GRANT SELECT ON learning.user_progress_view TO application_role;
11.2 Learning Path Summary View
sqlCREATE VIEW learning.path_summary_view AS
SELECT 
    lp.id as path_id,
    lp.title as path_title,
    lp.cognito_user_id,
    lp.created_at,
    COUNT(DISTINCT cm.ticket_id) as total_concepts,
    COUNT(DISTINCT CASE WHEN p.status = 'mastered' THEN p.ticket_id END) as mastered_concepts,
    COUNT(DISTINCT CASE WHEN p.status = 'studying' THEN p.ticket_id END) as studying_concepts,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN p.status = 'mastered' THEN p.ticket_id END) / 
          NULLIF(COUNT(DISTINCT cm.ticket_id), 0), 2) as completion_percentage
FROM learning.paths lp
LEFT JOIN learning.concept_metadata cm ON lp.id = cm.path_id
LEFT JOIN learning.progress p ON cm.ticket_id = p.ticket_id 
    AND p.cognito_user_id = lp.cognito_user_id
GROUP BY lp.id, lp.title, lp.cognito_user_id, lp.created_at;
12. Migration Scripts
12.1 Initial Schema Creation
sql-- Run after Trac schema is created
CREATE SCHEMA IF NOT EXISTS learning;

-- Create all learning tables
-- ... (all CREATE TABLE statements from above)

-- Insert default data
INSERT INTO public.milestone (name, description) VALUES
    ('Machine Learning Fundamentals', 'Core ML concepts'),
    ('Deep Learning', 'Neural networks and advanced topics'),
    ('Data Science Basics', 'Statistics and data analysis');

-- Create application role
CREATE ROLE application_role;
GRANT USAGE ON SCHEMA learning TO application_role;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA learning TO application_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA learning TO application_role;
13. AWS-Specific Considerations
13.1 RDS Configuration
yamlParameter Group Settings:
  shared_preload_libraries: 'pg_stat_statements'
  log_statement: 'all'
  log_min_duration_statement: 1000  # Log slow queries
  max_connections: 200
  
Performance Insights:
  Enabled: true
  Retention: 7 days (free tier)
  
Automated Backups:
  Retention: 7 days (dev), 30 days (prod)
  Window: 03:00-04:00 UTC
13.2 ElastiCache Configuration
yamlRedis Configuration:
  Cluster Mode: Enabled
  Node Type: cache.r6g.large
  Number of Shards: 2
  Replicas per Shard: 1
  
  Parameter Group:
    maxmemory-policy: allkeys-lru
    timeout: 300
    tcp-keepalive: 60
14. Data Consistency Strategy
14.1 Eventual Consistency Model
mermaidflowchart LR
    A[Write to RDS] --> B[Transaction Commits]
    B --> C[Invalidate Cache Keys]
    C --> D[Update ElastiCache]
    D --> E[Eventual Consistency]
    
    F[Read Request] --> G{Cache Hit?}
    G -->|Yes| H[Return Cached]
    G -->|No| I[Read from RDS]
    I --> J[Update Cache]
    J --> K[Return Fresh Data]
This entity relationship design provides:

AWS Native: Leverages managed services for reliability
Secure: Cognito authentication throughout
Performant: Strategic caching with ElastiCache
Scalable: RDS with read replicas, ElastiCache clustering
Maintainable: Clear schema separation and relationships