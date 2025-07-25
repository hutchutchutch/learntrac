# Functional Requirements Document - Question-Based Learning MVP for Trac 1.4.4
1. Introduction
1.1 Purpose
This document defines the functional requirements for the MVP implementation of question-based learning paths in Trac 1.4.4. The system uses Neo4j Aura vector search to discover academic content, LLM-generated questions to test understanding, and AWS services for authentication, orchestration, and data persistence.
1.2 MVP Scope

Neo4j Aura vector search for academic chunk discovery
LLM question generation for each concept
Answer evaluation with scoring
Progress tracking based on answer scores
GraphViz knowledge graph visualization
Prerequisite validation from chunk metadata
AWS Cognito authentication
AWS API Gateway for service communication
AWS RDS PostgreSQL for data persistence
AWS ElastiCache for caching

1.3 Out of Scope for MVP

Content creation or chunk management in Neo4j Aura
Community features
Analytics beyond basic progress
Manual path editing
Multiple learning paths per user
Multi-tenancy support

2. Functional Requirements
2.1 Authentication (FR-AU)
FR-AU-1: AWS Cognito Integration
Priority: Critical
Description: Secure authentication using AWS Cognito
Requirements:

FR-AU-1.1: Configure Cognito User Pool for learners
FR-AU-1.2: Implement JWT token validation
FR-AU-1.3: Secure all API endpoints with Cognito
FR-AU-1.4: Include user_id in all API requests
FR-AU-1.5: Handle token refresh automatically

FR-AU-2: Trac Session Integration
Priority: Critical
Description: Map Cognito users to Trac sessions
Requirements:

FR-AU-2.1: Create Trac session on successful Cognito auth
FR-AU-2.2: Store Cognito user_id in session attributes
FR-AU-2.3: Validate JWT on each request
FR-AU-2.4: Logout clears both Trac and Cognito sessions
FR-AU-2.5: Handle session expiration gracefully

2.2 API Gateway Integration (FR-AG)
FR-AG-1: Service Routing
Priority: Critical
Description: Route requests through AWS API Gateway
Requirements:

FR-AG-1.1: Configure routes for Trac endpoints
FR-AG-1.2: Configure routes for Learning Service
FR-AG-1.3: Implement request/response transformations
FR-AG-1.4: Add CORS headers for browser access
FR-AG-1.5: Rate limiting per user

FR-AG-2: Authorization
Priority: Critical
Description: Validate Cognito tokens at API Gateway
Requirements:

FR-AG-2.1: Configure Cognito Authorizer
FR-AG-2.2: Validate JWT on every request
FR-AG-2.3: Extract user claims from token
FR-AG-2.4: Pass user context to services
FR-AG-2.5: Return 401 for invalid tokens

2.3 Wiki Integration (FR-WI)
FR-WI-1: Learning Path Wiki Macro
Priority: Critical
Description: Wiki macro for initiating learning path generation
Requirements:

FR-WI-1.1: Create [[LearningPath]] macro for Wiki pages
FR-WI-1.2: Validate user is authenticated via Cognito
FR-WI-1.3: Include JWT token in API Gateway requests
FR-WI-1.4: Show loading spinner during Neo4j Aura search
FR-WI-1.5: Display discovered chunks before ticket creation

FR-WI-2: Knowledge Graph Macro
Priority: High
Description: Wiki macro to display GraphViz knowledge graph
Requirements:

FR-WI-2.1: Create [[KnowledgeGraph]] macro
FR-WI-2.2: Fetch user-specific progress from RDS
FR-WI-2.3: Generate GraphViz PNG with clickable areas
FR-WI-2.4: Cache generated graphs in ElastiCache
FR-WI-2.5: Color nodes based on answer scores

2.4 Learning Path Generation (FR-LP)
FR-LP-1: Query Processing
Priority: Critical
Description: Process learning queries through LLM and Neo4j Aura
Requirements:

FR-LP-1.1: Accept authenticated requests via API Gateway
FR-LP-1.2: Generate 5 academic sentences via LLM
FR-LP-1.3: Create embeddings for sentences
FR-LP-1.4: Search Neo4j Aura for chunks >65% relevance
FR-LP-1.5: Cache results in ElastiCache (1 hour TTL)

FR-LP-2: Chunk Processing
Priority: Critical
Description: Extract learning data from Neo4j Aura chunks
Requirements:

FR-LP-2.1: Connect securely to Neo4j Aura
FR-LP-2.2: Extract subject for milestone grouping
FR-LP-2.3: Extract concept for ticket summary
FR-LP-2.4: Extract has_prerequisite relationship
FR-LP-2.5: Validate chunk data structure

FR-LP-3: Question Generation
Priority: Critical
Description: Generate questions for each concept via API Gateway
Requirements:

FR-LP-3.1: Route to LLM service through API Gateway
FR-LP-3.2: Base question on chunk content
FR-LP-3.3: Set question difficulty (1-5)
FR-LP-3.4: Include learning query as context
FR-LP-3.5: Store in RDS with user association

2.5 RDS Database Management (FR-DB)
FR-DB-1: Trac Schema Setup
Priority: Critical
Description: Initialize Trac schema in AWS RDS PostgreSQL
Requirements:

FR-DB-1.1: Create all standard Trac tables
FR-DB-1.2: Initialize ticket workflow configuration
FR-DB-1.3: Set up milestone and component tables
FR-DB-1.4: Configure session management tables
FR-DB-1.5: Add required indexes for performance

FR-DB-2: Learning Schema Creation
Priority: Critical
Description: Create learning-specific schema in RDS
Requirements:

FR-DB-2.1: Create learning schema namespace
FR-DB-2.2: Add paths, progress, prerequisites tables
FR-DB-2.3: Set up foreign key relationships
FR-DB-2.4: Create indexes for query performance
FR-DB-2.5: Add constraints for data integrity

2.6 Ticket Management (FR-TM)
FR-TM-1: Concept Ticket Creation
Priority: Critical
Description: Create Trac tickets in RDS for learning concepts
Requirements:

FR-TM-1.1: Insert into RDS ticket table
FR-TM-1.2: Associate with Cognito user_id
FR-TM-1.3: Use chunk content as description
FR-TM-1.4: Assign to subject milestone
FR-TM-1.5: Set initial status to 'new'

FR-TM-2: Learning Fields Storage
Priority: Critical
Description: Store learning data in RDS ticket_custom
Requirements:

FR-TM-2.1: Store 'question' text in RDS
FR-TM-2.2: Store 'question_difficulty' (1-5)
FR-TM-2.3: Store 'question_context' (original query)
FR-TM-2.4: Store 'expected_answer' for evaluation
FR-TM-2.5: Store prerequisite relationships

2.7 Answer Evaluation (FR-AE)
FR-AE-1: Answer Submission
Priority: Critical
Description: Process answer submissions through API Gateway
Requirements:

FR-AE-1.1: Validate Cognito token
FR-AE-1.2: Submit to Learning Service via API Gateway
FR-AE-1.3: Store attempt in RDS
FR-AE-1.4: Update ElastiCache with progress
FR-AE-1.5: Handle evaluation timeouts

FR-AE-2: LLM Evaluation
Priority: Critical
Description: Evaluate answers using LLM via API Gateway
Requirements:

FR-AE-2.1: Route to LLM service through API Gateway
FR-AE-2.2: Include question context in evaluation
FR-AE-2.3: Return score (0.0 to 1.0)
FR-AE-2.4: Provide detailed feedback
FR-AE-2.5: Cache evaluation results

FR-AE-3: Progress Updates
Priority: High
Description: Update progress in RDS and cache
Requirements:

FR-AE-3.1: Update RDS learning.progress table
FR-AE-3.2: Update ticket status if mastered
FR-AE-3.3: Invalidate ElastiCache entries
FR-AE-3.4: Trigger graph regeneration
FR-AE-3.5: Maintain answer history in RDS

2.8 Caching Strategy (FR-CS)
FR-CS-1: ElastiCache Integration
Priority: High
Description: Use AWS ElastiCache for performance
Requirements:

FR-CS-1.1: Cache Neo4j search results (1 hour)
FR-CS-1.2: Cache user progress data (15 minutes)
FR-CS-1.3: Cache generated graphs (until progress change)
FR-CS-1.4: Implement cache invalidation
FR-CS-1.5: Handle cache misses gracefully

FR-CS-2: Session Data
Priority: High
Description: Store session data in ElastiCache
Requirements:

FR-CS-2.1: Store active Cognito sessions
FR-CS-2.2: Cache user preferences
FR-CS-2.3: Track active learning paths
FR-CS-2.4: Implement session timeout
FR-CS-2.5: Clear on logout

2.9 Learning Service API (FR-LS)
FR-LS-1: Path Generation Endpoint
Priority: Critical
Description: API for Neo4j Aura search via API Gateway
Requirements:

FR-LS-1.1: POST /api/v1/learning-paths/generate
FR-LS-1.2: Validate Cognito token
FR-LS-1.3: Search Neo4j Aura vector store
FR-LS-1.4: Cache in ElastiCache
FR-LS-1.5: Return chunks with metadata

FR-LS-2: Ticket Creation Endpoint
Priority: Critical
Description: API for creating tickets in RDS
Requirements:

FR-LS-2.1: POST /api/v1/learning-paths/create
FR-LS-2.2: Validate user authorization
FR-LS-2.3: Create tickets in RDS
FR-LS-2.4: Establish prerequisites in RDS
FR-LS-2.5: Return created ticket IDs

FR-LS-3: Answer Evaluation Endpoint
Priority: Critical
Description: API for evaluating answers
Requirements:

FR-LS-3.1: PUT /api/v1/progress/{ticket_id}/submit-answer
FR-LS-3.2: Verify user owns ticket
FR-LS-3.3: Retrieve from RDS
FR-LS-3.4: Update RDS and ElastiCache
FR-LS-3.5: Return evaluation results

3. Data Requirements
3.1 Neo4j Aura Configuration

Configured instance with vector index
Pre-loaded academic chunks
Secure connection credentials
Read-only access from Learning Service

3.2 RDS PostgreSQL Schema

Complete Trac 1.4.4 schema
Learning schema with custom tables
User associations via Cognito ID
Optimized indexes for queries

3.3 ElastiCache Redis Structure

Search results: search:{query}:{user_id} (1 hour TTL)
User progress: progress:{user_id}:{ticket_id} (15 min TTL)
Graph cache: graph:{milestone}:{user_id} (until invalidated)
Session data: session:{cognito_id} (2 hour TTL)

4. Non-Functional Requirements
4.1 Performance

API Gateway latency: <100ms overhead
Neo4j Aura search: <2 seconds for 20 chunks
RDS queries: <100ms for indexed queries
ElastiCache operations: <10ms
End-to-end response: <3 seconds

4.2 Security

All endpoints secured with Cognito
API Gateway request validation
RDS encryption at rest and in transit
Neo4j Aura secure connection
No direct database access from browser

4.3 Reliability

API Gateway retry logic
RDS Multi-AZ deployment (production)
ElastiCache automatic failover
Graceful degradation on cache miss
Circuit breakers for external services

4.4 Scalability

API Gateway auto-scaling
RDS read replicas for queries
ElastiCache cluster mode
Stateless service containers
Horizontal scaling for Learning Service

5. Integration Requirements
5.1 AWS Service Integration

Cognito User Pool configuration
API Gateway REST API setup
RDS PostgreSQL 15 compatibility
ElastiCache Redis 7 protocol
CloudWatch logging for all services

5.2 External Service Integration

Neo4j Aura cloud instance
LLM API (OpenAI/Anthropic) via API Gateway
GraphViz binary in containers

6. Constraints
6.1 Technical Constraints

Trac 1.4.4 Python 2.7 compatibility
Neo4j Aura connection limits
API Gateway request size limits
RDS connection pool management
ElastiCache memory limits

6.2 AWS Service Limits

Cognito user pool quotas
API Gateway rate limits
RDS storage and IOPS limits
ElastiCache node types
Regional service availability