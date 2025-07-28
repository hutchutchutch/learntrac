#!/bin/bash
# LearnTrac API Testing with curl
# Replace YOUR_SESSION_TOKEN with actual session token from browser

BASE_URL="http://localhost:8001"
AUTH_HEADER="Cookie: trac_auth=YOUR_SESSION_TOKEN"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}LearnTrac API curl Examples${NC}"
echo "================================"

# 1. LLM Generate Question
echo -e "\n${GREEN}1. Generate Single Question${NC}"
curl -X POST "${BASE_URL}/api/learntrac/llm/generate-question" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "chunk_content": "Python functions are reusable blocks of code that perform specific tasks. They are defined using the def keyword, followed by the function name and parameters in parentheses.",
    "concept": "Python Functions",
    "difficulty": 3,
    "context": "Introduction to Programming",
    "question_type": "comprehension"
  }' | jq '.'

# 2. LLM Generate Multiple Questions
echo -e "\n${GREEN}2. Generate Multiple Questions${NC}"
curl -X POST "${BASE_URL}/api/learntrac/llm/generate-multiple-questions" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "chunk_content": "Object-oriented programming (OOP) is a programming paradigm based on the concept of objects, which contain data (attributes) and code (methods).",
    "concept": "Object-Oriented Programming",
    "count": 3,
    "difficulty_range": [2, 4],
    "question_types": ["comprehension", "application", "analysis"]
  }' | jq '.'

# 3. Analyze Content
echo -e "\n${GREEN}3. Analyze Content Difficulty${NC}"
curl -X POST "${BASE_URL}/api/learntrac/llm/analyze-content" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
    "analysis_type": "difficulty"
  }' | jq '.'

# 4. Vector Search
echo -e "\n${GREEN}4. Vector Search${NC}"
curl -X POST "${BASE_URL}/api/learntrac/vector/search" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "query": "How do neural networks learn from data?",
    "min_score": 0.65,
    "limit": 5,
    "include_prerequisites": true,
    "include_dependents": false
  }' | jq '.'

# 5. Create Chunk
echo -e "\n${GREEN}5. Create New Chunk${NC}"
curl -X POST "${BASE_URL}/api/learntrac/vector/chunks" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "content": "Recursion is a programming technique where a function calls itself to solve a problem.",
    "subject": "Computer Science",
    "concept": "Recursion",
    "has_prerequisite": [],
    "metadata": {
      "difficulty_level": 3,
      "estimated_learning_time": "30 minutes"
    }
  }' | jq '.'

# 6. Enhanced Vector Search
echo -e "\n${GREEN}6. Enhanced Vector Search${NC}"
curl -X POST "${BASE_URL}/api/learntrac/vector/search/enhanced" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "query": "neural network training techniques",
    "generate_sentences": 5,
    "min_score": 0.7,
    "limit": 10,
    "include_prerequisites": true,
    "include_generated_context": true
  }' | jq '.'

# 7. Compare Search Methods
echo -e "\n${GREEN}7. Compare Regular vs Enhanced Search${NC}"
curl -X POST "${BASE_URL}/api/learntrac/vector/search/compare" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "query": "database optimization",
    "min_score": 0.65,
    "limit": 10
  }' | jq '.'

# 8. Bulk Vector Search
echo -e "\n${GREEN}8. Bulk Vector Search${NC}"
curl -X POST "${BASE_URL}/api/learntrac/vector/search/bulk" \
  -H "Content-Type: application/json" \
  -H "${AUTH_HEADER}" \
  -d '{
    "queries": [
      "What is polymorphism in OOP?",
      "How do databases handle transactions?",
      "Explain REST API principles"
    ],
    "min_score": 0.65,
    "limit_per_query": 3
  }' | jq '.'

# 7. Health Checks
echo -e "\n${GREEN}7. Health Check - LLM${NC}"
curl -X GET "${BASE_URL}/api/learntrac/llm/health" \
  -H "${AUTH_HEADER}" | jq '.'

echo -e "\n${GREEN}8. Health Check - Vector Search${NC}"
curl -X GET "${BASE_URL}/api/learntrac/vector/health" \
  -H "${AUTH_HEADER}" | jq '.'

# 9. Get Question Types
echo -e "\n${GREEN}9. Get Available Question Types${NC}"
curl -X GET "${BASE_URL}/api/learntrac/llm/question-types" \
  -H "${AUTH_HEADER}" | jq '.'

# 10. Get Prerequisites for a Chunk
echo -e "\n${GREEN}10. Get Prerequisites${NC}"
# Replace chunk_id with actual chunk ID
curl -X GET "${BASE_URL}/api/learntrac/vector/chunks/chunk_example_001/prerequisites?max_depth=3" \
  -H "${AUTH_HEADER}" | jq '.'

# Function to test with basic auth instead of cookie
test_with_basic_auth() {
  echo -e "\n${GREEN}Testing with Basic Auth${NC}"
  curl -X POST "${BASE_URL}/api/learntrac/llm/generate-question" \
    -H "Content-Type: application/json" \
    -u "admin:admin" \
    -d '{
      "chunk_content": "Test content for basic auth",
      "concept": "Test Concept",
      "difficulty": 1
    }' | jq '.'
}

# Function to generate questions from specific chunks
test_generate_from_chunks() {
  echo -e "\n${GREEN}Generate Questions from Chunks${NC}"
  # Replace with actual chunk IDs from your Neo4j database
  curl -X POST "${BASE_URL}/api/learntrac/llm/generate-from-chunks" \
    -H "Content-Type: application/json" \
    -H "${AUTH_HEADER}" \
    -d '{
      "chunk_ids": ["chunk_001", "chunk_002", "chunk_003"],
      "difficulty": 3,
      "questions_per_chunk": 2
    }' | jq '.'
}

# Function to create prerequisite relationship
test_create_prerequisite() {
  echo -e "\n${GREEN}Create Prerequisite Relationship${NC}"
  curl -X POST "${BASE_URL}/api/learntrac/vector/prerequisites" \
    -H "Content-Type: application/json" \
    -H "${AUTH_HEADER}" \
    -d '{
      "from_chunk_id": "chunk_advanced_001",
      "to_chunk_id": "chunk_basic_001",
      "relationship_type": "STRONG"
    }' | jq '.'
}

# Admin-only endpoints
test_admin_endpoints() {
  echo -e "\n${GREEN}Admin Endpoints${NC}"
  
  # LLM Stats
  echo -e "\n${BLUE}LLM Statistics:${NC}"
  curl -X GET "${BASE_URL}/api/learntrac/llm/stats" \
    -H "${AUTH_HEADER}" | jq '.'
}

# Stress test function
stress_test_questions() {
  echo -e "\n${GREEN}Stress Test - Generating 10 Questions${NC}"
  for i in {1..10}; do
    echo -e "\n${BLUE}Request $i:${NC}"
    curl -s -X POST "${BASE_URL}/api/learntrac/llm/generate-question" \
      -H "Content-Type: application/json" \
      -H "${AUTH_HEADER}" \
      -d "{
        \"chunk_content\": \"Test content for stress test request $i\",
        \"concept\": \"Stress Test Concept $i\",
        \"difficulty\": $((($i % 5) + 1))
      }" | jq -c '{question: .question, status: .error}'
    sleep 1  # Avoid rate limiting
  done
}

# Usage instructions
usage() {
  echo -e "\n${BLUE}Usage:${NC}"
  echo "1. Update AUTH_HEADER with your session token"
  echo "2. Run individual tests or uncomment functions below"
  echo "3. Make sure jq is installed for JSON formatting"
}

# Uncomment to run specific tests
# test_with_basic_auth
# test_generate_from_chunks
# test_create_prerequisite
# test_admin_endpoints
# stress_test_questions

usage