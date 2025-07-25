Executive Summary
This product vision guide outlines the MVP for transforming Trac 1.4.4 into a question-based learning management system. By leveraging Neo4j Aura for academic content discovery and LLM-powered question generation, we enable learners to master concepts through active question-answering while using Trac's proven project management infrastructure. The system is deployed on AWS with Cognito authentication, API Gateway for service communication, RDS PostgreSQL for data persistence, and ElastiCache for caching.
Vision Statement
Transform Trac into a cloud-native personal learning platform where learners discover academic knowledge through AI-powered vector search, master concepts by answering generated questions, and track their progress through familiar project management visualizations—all secured by AWS Cognito and orchestrated through API Gateway.
MVP Core Features
1. Instant Learning Paths via Vector Search
Transform learning queries into structured paths by searching Neo4j Aura's knowledge base of academic chunks, returning the most relevant content based on semantic similarity.
2. Concept Mapping with Questions
Each discovered chunk becomes a learning ticket with an LLM-generated question that tests understanding of the concept.
3. Progress Tracking through Answer Evaluation
Track learning progress by evaluating student answers against expected responses, with scores determining mastery status.
4. Knowledge Dependencies from Chunks
Map prerequisite relationships between concepts using metadata from Neo4j Aura chunks, ensuring proper learning sequence.
5. Self-Paced Learning with Answer History
Learn at individual pace with time tracking, answer attempts history, and personal notes on each concept.
6. Knowledge Graph Visualization
Display learning paths as GraphViz-generated images showing concept relationships, prerequisites, and progress through color coding.
The Learning-as-a-Project Philosophy
We reimagine Trac's components for question-based learning:

Ticket → Learning Concept with Question
Milestone → Subject Grouping (from chunk metadata)
Roadmap → Learning Path Progress
Dependencies → Prerequisite Concepts (from chunk relationships)
Status Workflow → Answer-Based Progress (new → studying → mastered)

User Persona
The Self-Directed Learner

Context: Individual seeking to master academic topics independently
Need: Structured learning with clear questions to test understanding
Use Case: Enters "I want to understand machine learning" and receives learning path with questions for each concept
Authentication: Signs in via AWS Cognito to access personalized learning

MVP Feature Details
1. Secure Wiki-Based Learning Path Input
Users access learning through a Wiki macro after authenticating via Cognito:
[[LearningPath(I want to learn quantum computing)]]
This renders an input form that:

Validates user's Cognito JWT token
Accepts natural language learning queries
Sends authenticated request to Learning Service via API Gateway
Displays discovered chunks from Neo4j Aura
Creates tickets with questions on confirmation

2. Neo4j Aura Vector Search Process
The Learning Service (accessed via API Gateway):

Validates Cognito token from request
Generates 5 academic sentences from the query using LLM
Creates embeddings from these sentences
Searches Neo4j Aura for chunks with >65% relevance
Returns up to 20 most relevant chunks
Caches results in AWS ElastiCache for 1 hour

3. Chunk-to-Ticket Transformation in RDS
Each Neo4j chunk is transformed into a ticket in AWS RDS PostgreSQL:

Creates Trac schema ticket with learning concept
Stores question data in ticket_custom table
Links prerequisites in learning schema
Associates with authenticated user

4. Question-Based Progress
Learning progress tracked in RDS and cached in ElastiCache:

Question displayed prominently in ticket view
Text area for answer submission
LLM evaluation providing score (0-1) and feedback
Score ≥ 0.8 marks concept as mastered
Answer history with scores and feedback

5. Prerequisite Management
Dependencies enforced through RDS relationships:

Prerequisite relationships from Neo4j chunks
Ticket linking for dependencies
Validation before allowing concept study
Visual representation in knowledge graph

6. GraphViz Knowledge Graph
Server-generated visualization showing:

Concepts as nodes (from RDS tickets)
Prerequisites as directed edges
Progress through color coding:

Gray: Not started
Orange: Studying (answer attempted)
Green: Mastered (score ≥ 0.8)


Clickable nodes linking to ticket pages

Technical Architecture Overview
AWS Infrastructure

AWS Cognito: User authentication and JWT tokens
AWS API Gateway: Service orchestration and routing
AWS RDS PostgreSQL: Trac schema + learning progress
Neo4j Aura: Academic chunks with vector embeddings
AWS ElastiCache Redis: Result caching and session data

Two-Container System

Trac Container (Python 2.7): Wiki macros, ticket customization, GraphViz
Learning Service (Python 3.11): Neo4j search, question generation, answer evaluation

Secure Data Flow

Cognito JWT → API Gateway validation
Query → LLM sentences → Neo4j Aura vector search
Chunks → RDS tickets with questions
Student answers → LLM evaluation via API Gateway
Scores → Progress tracking → Graph updates

MVP Implementation Scope
What's Included

Neo4j Aura vector search for academic content
LLM question generation per concept
Answer evaluation with scoring
Progress tracking based on scores
GraphViz visualization
Prerequisite validation
AWS Cognito authentication
API Gateway service orchestration

What's Excluded

Community features
Analytics dashboards beyond basic progress
Content creation tools
Manual path editing
Mobile-native applications
Multi-tenancy support

Example Learning Flow
User Authentication: Sign in via Cognito → Receive JWT token
Query: "I want to understand blockchain technology"
Neo4j Aura Returns:
Chunk 1: {
  content: "Cryptographic hash functions ensure data integrity...",
  subject: "Blockchain Fundamentals",
  concept: "Hash Functions",
  has_prerequisite: null,
  prerequisite_for: "Blocks"
}

Chunk 2: {
  content: "Blocks contain transactions and reference previous blocks...",
  subject: "Blockchain Fundamentals", 
  concept: "Blocks",
  has_prerequisite: "Hash Functions",
  prerequisite_for: "Blockchain"
}
Generated Tickets in RDS:
Ticket #101: Hash Functions
Question: "Explain how cryptographic hash functions ensure data integrity in blockchain systems."
Expected Answer: "Hash functions create fixed-size outputs..."

Ticket #102: Blocks  
Question: "Describe the structure of a block and how it references previous blocks."
Expected Answer: "A block contains a header with previous hash..."
Why This Approach Works

Enterprise Security: AWS Cognito provides robust authentication
Real Academic Content: Neo4j Aura contains verified educational chunks
Active Learning: Questions require understanding, not memorization
Objective Progress: LLM scoring provides measurable advancement
Familiar Interface: Uses Trac's existing ticket and roadmap views
Clear Dependencies: Prerequisite relationships guide learning order
Cloud Native: Leverages AWS managed services for reliability

MVP Success Criteria

Cognito authentication working for all endpoints
Vector search returns relevant chunks in <2 seconds
Questions generated for all concepts
Answer evaluation provides meaningful feedback
Progress visualization through existing Trac views
Prerequisite validation prevents skipping concepts
API Gateway handles service communication securely

Conclusion
This MVP delivers a complete question-based learning system by combining Neo4j Aura's academic knowledge base with Trac's project management features, all secured by AWS Cognito and orchestrated through API Gateway. Learners progress by answering questions about concepts discovered through AI-powered search, with clear visualization of their learning journey and enterprise-grade security.
