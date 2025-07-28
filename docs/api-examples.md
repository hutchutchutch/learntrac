# LearnTrac API Examples for Swagger UI Testing

## LLM Endpoints (/api/learntrac/llm)

### 1. Generate Question - POST /api/learntrac/llm/generate-question

Generate a single question based on learning content.

**Request Body:**
```json
{
  "chunk_content": "Python functions are reusable blocks of code that perform specific tasks. They are defined using the 'def' keyword, followed by the function name and parameters in parentheses. Functions can accept arguments and return values using the 'return' statement. They help in organizing code, avoiding repetition, and making programs more modular.",
  "concept": "Python Functions",
  "difficulty": 3,
  "context": "Introduction to Programming course",
  "question_type": "comprehension"
}
```

**Response:**
```json
{
  "question": "What is the primary purpose of using functions in Python programming, and what keyword is used to define them?",
  "expected_answer": "The primary purpose of using functions in Python is to create reusable blocks of code that perform specific tasks, helping to organize code, avoid repetition, and make programs more modular. Functions are defined using the 'def' keyword, followed by the function name and parameters in parentheses.",
  "concept": "Python Functions",
  "difficulty": 3,
  "generated_at": "2024-01-15T10:30:00Z",
  "question_length": 95,
  "answer_length": 245,
  "error": null
}
```

### 2. Generate Multiple Questions - POST /api/learntrac/llm/generate-multiple-questions

Generate multiple questions for comprehensive assessment.

**Request Body:**
```json
{
  "chunk_content": "Object-oriented programming (OOP) is a programming paradigm based on the concept of objects, which contain data (attributes) and code (methods). The four main principles of OOP are encapsulation, inheritance, polymorphism, and abstraction. Classes serve as blueprints for creating objects.",
  "concept": "Object-Oriented Programming",
  "count": 3,
  "difficulty_range": [2, 4],
  "question_types": ["comprehension", "application", "analysis"]
}
```

**Response:**
```json
{
  "concept": "Object-Oriented Programming",
  "requested_count": 3,
  "generated_count": 3,
  "questions": [
    {
      "question": "What are the four main principles of object-oriented programming?",
      "expected_answer": "The four main principles of object-oriented programming are: 1) Encapsulation - bundling data and methods together within objects, 2) Inheritance - allowing classes to inherit properties and methods from other classes, 3) Polymorphism - enabling objects to take multiple forms, and 4) Abstraction - hiding complex implementation details.",
      "concept": "Object-Oriented Programming",
      "difficulty": 2,
      "generated_at": "2024-01-15T10:31:00Z",
      "question_length": 65,
      "answer_length": 310
    },
    {
      "question": "How would you use inheritance to create a Student class that extends a Person class in an OOP design?",
      "expected_answer": "To create a Student class that inherits from Person, you would define the Student class with Person as its parent class. The Student class would inherit all attributes and methods from Person (like name, age) and add student-specific attributes (like student_id, courses). This demonstrates the 'is-a' relationship where Student is a specialized type of Person.",
      "concept": "Object-Oriented Programming",
      "difficulty": 3,
      "generated_at": "2024-01-15T10:31:05Z",
      "question_length": 102,
      "answer_length": 335
    },
    {
      "question": "Compare and contrast encapsulation and abstraction in OOP. How do they work together to improve code design?",
      "expected_answer": "Encapsulation and abstraction are related but distinct concepts. Encapsulation bundles data and methods together within objects and controls access through visibility modifiers (private, public). Abstraction hides complex implementation details and shows only essential features. They work together by using encapsulation to implement abstraction - private members hide complexity while public interfaces provide simplified access.",
      "concept": "Object-Oriented Programming",
      "difficulty": 4,
      "generated_at": "2024-01-15T10:31:10Z",
      "question_length": 108,
      "answer_length": 385
    }
  ]
}
```

### 3. Generate from Chunks - POST /api/learntrac/llm/generate-from-chunks

Generate questions from multiple Neo4j chunks.

**Request Body:**
```json
{
  "chunk_ids": ["chunk_a1b2c3d4e5f6", "chunk_b2c3d4e5f6g7", "chunk_c3d4e5f6g7h8"],
  "difficulty": 3,
  "questions_per_chunk": 2
}
```

**Response:**
```json
{
  "total_chunks_requested": 3,
  "successful_chunks": 3,
  "failed_chunks": [],
  "total_questions_generated": 6,
  "questions": [
    {
      "question": "What is the difference between a list and a tuple in Python?",
      "expected_answer": "The main differences between lists and tuples in Python are: 1) Lists are mutable (can be modified after creation) while tuples are immutable (cannot be changed), 2) Lists use square brackets [] while tuples use parentheses (), 3) Lists are typically used for homogeneous data while tuples often store heterogeneous data, 4) Tuples are generally faster and use less memory than lists.",
      "chunk_id": "chunk_a1b2c3d4e5f6",
      "subject": "Python Data Structures",
      "concept": "Lists and Tuples",
      "difficulty": 3,
      "generated_at": "2024-01-15T10:32:00Z"
    }
  ]
}
```

### 4. Analyze Content - POST /api/learntrac/llm/analyze-content

Analyze content for educational insights.

**Request Body:**
```json
{
  "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data, identify patterns, and make decisions. Common types include supervised learning, unsupervised learning, and reinforcement learning.",
  "analysis_type": "difficulty"
}
```

**Response:**
```json
{
  "content_length": 301,
  "analysis_type": "difficulty",
  "analysis": "{\n  \"difficulty_rating\": 3,\n  \"reasoning\": \"This content introduces technical concepts but explains them in accessible terms. It requires understanding of abstract concepts but doesn't assume deep mathematical knowledge.\",\n  \"prerequisites\": [\"Basic programming knowledge\", \"Understanding of data and algorithms\", \"Familiarity with AI concepts\"],\n  \"target_audience_level\": \"Undergraduate computer science students or professionals new to ML\"\n}",
  "generated_at": "2024-01-15T10:33"
}
```

## Vector Search Endpoints (/api/learntrac/vector)

### 1. Vector Search - POST /api/learntrac/vector/search

Perform semantic search on learning content.

**Request Body:**
```json
{
  "query": "How do neural networks learn from data?",
  "min_score": 0.7,
  "limit": 10,
  "include_prerequisites": true,
  "include_dependents": false
}
```

**Response:**
```json
{
  "query": "How do neural networks learn from data?",
  "results": [
    {
      "id": "chunk_nn_learning_001",
      "content": "Neural networks learn through a process called backpropagation. During training, the network makes predictions, calculates the error between predictions and actual values, and adjusts weights to minimize this error. This iterative process continues until the network achieves acceptable accuracy.",
      "subject": "Deep Learning",
      "concept": "Neural Network Training",
      "score": 0.89,
      "prerequisites": [
        {
          "id": "chunk_ml_basics_001",
          "content": "Machine learning fundamentals including supervised learning concepts",
          "subject": "Machine Learning",
          "concept": "ML Basics",
          "depth": 1
        }
      ]
    },
    {
      "id": "chunk_gradient_desc_001",
      "content": "Gradient descent is an optimization algorithm used to minimize the loss function in neural networks. It calculates gradients of the loss with respect to weights and updates them in the opposite direction of the gradient.",
      "subject": "Deep Learning",
      "concept": "Gradient Descent",
      "score": 0.82,
      "prerequisites": [
        {
          "id": "chunk_calculus_001",
          "content": "Understanding of derivatives and partial derivatives",
          "subject": "Mathematics",
          "concept": "Calculus",
          "depth": 1
        }
      ]
    }
  ],
  "count": 2,
  "min_score_used": 0.7
}
```

### 2. Create Chunk - POST /api/learntrac/vector/chunks

Create a new learning chunk with embedding.

**Request Body:**
```json
{
  "content": "Recursion is a programming technique where a function calls itself to solve a problem. Each recursive call works on a smaller subset of the problem until reaching a base case that can be solved directly. Common examples include factorial calculation and tree traversal.",
  "subject": "Computer Science",
  "concept": "Recursion",
  "has_prerequisite": ["chunk_functions_001", "chunk_stack_memory_001"],
  "metadata": {
    "difficulty_level": 3,
    "estimated_learning_time": "30 minutes",
    "programming_language": "Python"
  }
}
```

**Response:**
```json
{
  "chunk_id": "chunk_7a8b9c0d1e2f",
  "message": "Chunk created successfully"
}
```

### 3. Bulk Vector Search - POST /api/learntrac/vector/search/bulk

Search for multiple queries simultaneously.

**Request Body:**
```json
{
  "queries": [
    "What is polymorphism in OOP?",
    "How do databases handle transactions?",
    "Explain REST API principles"
  ],
  "min_score": 0.65,
  "limit_per_query": 5
}
```

**Response:**
```json
{
  "searches": [
    {
      "query": "What is polymorphism in OOP?",
      "results": [
        {
          "id": "chunk_poly_001",
          "content": "Polymorphism allows objects of different types to be treated as objects of a common base type. It enables a single interface to represent different underlying forms (data types).",
          "subject": "Object-Oriented Programming",
          "concept": "Polymorphism",
          "score": 0.92
        }
      ],
      "count": 1
    },
    {
      "query": "How do databases handle transactions?",
      "results": [
        {
          "id": "chunk_acid_001",
          "content": "Databases handle transactions using ACID properties: Atomicity ensures all operations complete or none do, Consistency maintains data integrity, Isolation prevents interference between transactions, and Durability guarantees committed changes persist.",
          "subject": "Database Systems",
          "concept": "ACID Transactions",
          "score": 0.88
        }
      ],
      "count": 1
    },
    {
      "query": "Explain REST API principles",
      "results": [
        {
          "id": "chunk_rest_001",
          "content": "REST (Representational State Transfer) APIs follow six principles: Client-Server architecture, Statelessness, Cacheability, Uniform Interface, Layered System, and Code on Demand (optional). Resources are identified by URIs and manipulated using standard HTTP methods.",
          "subject": "Web Development",
          "concept": "REST Architecture",
          "score": 0.85
        }
      ],
      "count": 1
    }
  ],
  "total_queries": 3,
  "successful_queries": 3
}
```

### 4. Create Prerequisite Relationship - POST /api/learntrac/vector/prerequisites

Link chunks with prerequisite relationships.

**Request Body:**
```json
{
  "from_chunk_id": "chunk_advanced_ml_001",
  "to_chunk_id": "chunk_linear_algebra_001",
  "relationship_type": "STRONG"
}
```

**Response:**
```json
{
  "message": "Prerequisite relationship created successfully"
}
```

### 5. Enhanced Vector Search - POST /api/learntrac/vector/search/enhanced

Perform semantic search with LLM-generated academic context for improved relevance.

**Request Body:**
```json
{
  "query": "machine learning algorithms",
  "generate_sentences": 5,
  "min_score": 0.7,
  "limit": 20,
  "include_prerequisites": true,
  "include_generated_context": true
}
```

**Response:**
```json
{
  "original_query": "machine learning algorithms",
  "search_method": "enhanced",
  "results": [
    {
      "id": "chunk_ml_fundamentals_001",
      "content": "Machine learning algorithms are computational methods that enable systems to learn patterns from data without explicit programming. They fall into three main categories: supervised learning (with labeled data), unsupervised learning (finding hidden patterns), and reinforcement learning (learning through interaction).",
      "subject": "Machine Learning",
      "concept": "ML Algorithm Categories",
      "score": 0.92,
      "prerequisites": [
        {
          "id": "chunk_statistics_001",
          "content": "Statistical foundations including probability distributions and hypothesis testing",
          "subject": "Mathematics",
          "concept": "Statistics",
          "depth": 1
        }
      ]
    },
    {
      "id": "chunk_supervised_learning_001",
      "content": "Supervised learning algorithms include decision trees, random forests, support vector machines, and neural networks. These algorithms learn from labeled training data to make predictions on new, unseen data.",
      "subject": "Machine Learning",
      "concept": "Supervised Learning",
      "score": 0.88
    }
  ],
  "result_count": 2,
  "min_score_used": 0.7,
  "generated_context": {
    "sentences": [
      "Machine learning algorithms encompass a diverse range of computational techniques including decision trees, neural networks, support vector machines, and ensemble methods, each designed to identify patterns and make predictions from data.",
      "The mathematical foundations of machine learning algorithms involve linear algebra for data representation, calculus for optimization, probability theory for uncertainty modeling, and statistics for inference and validation.",
      "Supervised learning algorithms such as regression and classification models learn from labeled training data, while unsupervised algorithms like clustering and dimensionality reduction discover hidden structures in unlabeled datasets.",
      "Modern machine learning algorithms leverage techniques from computer science, mathematics, and domain-specific knowledge, requiring understanding of algorithm complexity, convergence properties, and generalization capabilities.",
      "Applications of machine learning algorithms span natural language processing, computer vision, recommendation systems, predictive analytics, and autonomous systems, each requiring careful selection of appropriate algorithms and hyperparameter tuning."
    ],
    "sentence_count": 5,
    "combined_text": "Machine learning algorithms encompass a diverse range of computational techniques... [full text]",
    "total_length": 842
  }
}
```

### 6. Compare Search Methods - POST /api/learntrac/vector/search/compare

Compare regular vs enhanced search to understand the impact of LLM expansion.

**Request Body:**
```json
{
  "query": "database indexing",
  "min_score": 0.65,
  "limit": 10
}
```

**Response:**
```json
{
  "query": "database indexing",
  "comparison": {
    "regular_search": {
      "result_count": 8,
      "top_scores": [0.82, 0.78, 0.73, 0.71, 0.68],
      "unique_results": 3
    },
    "enhanced_search": {
      "result_count": 12,
      "top_scores": [0.89, 0.86, 0.83, 0.80, 0.77],
      "unique_results": 7,
      "generated_sentences": [
        "Database indexing is a data structure technique that improves the speed of data retrieval operations on database tables at the cost of additional writes and storage space for maintaining the index data structure.",
        "Common indexing methods include B-tree indexes for range queries, hash indexes for equality searches, bitmap indexes for low-cardinality columns, and full-text indexes for searching text content within database records.",
        "The theory behind database indexing draws from computer science fundamentals including data structures, algorithm analysis, storage systems, and query optimization techniques used in modern relational and NoSQL databases.",
        "Performance implications of database indexing involve trade-offs between query speed, insert/update/delete operations, storage requirements, and index maintenance overhead in production database systems.",
        "Advanced indexing concepts encompass covering indexes, partial indexes, functional indexes, multi-column indexes, and index intersection strategies employed by query optimizers in enterprise database management systems."
      ]
    },
    "overlap": {
      "common_results": 5,
      "percentage": 41.67
    }
  },
  "regular_results": [
    {
      "id": "chunk_db_index_001",
      "content": "Database indexes are special lookup tables that the database search engine uses to speed up data retrieval.",
      "score": 0.82
    }
  ],
  "enhanced_results": [
    {
      "id": "chunk_db_theory_001",
      "content": "The theoretical foundations of database indexing include B-tree algorithms, hash functions, and search optimization strategies.",
      "score": 0.89
    }
  ]
}
```

### 7. Get Prerequisites - GET /api/learntrac/vector/chunks/{chunk_id}/prerequisites

Get prerequisite chain for a learning chunk.

**Example:** GET /api/learntrac/vector/chunks/chunk_neural_nets_001/prerequisites?max_depth=3

**Response:**
```json
{
  "chunk_id": "chunk_neural_nets_001",
  "prerequisites": [
    {
      "id": "chunk_linear_algebra_001",
      "content": "Linear algebra fundamentals including matrix operations and vector spaces",
      "subject": "Mathematics",
      "concept": "Linear Algebra",
      "depth": 1
    },
    {
      "id": "chunk_calculus_001",
      "content": "Calculus concepts including derivatives and chain rule",
      "subject": "Mathematics",
      "concept": "Calculus",
      "depth": 1
    },
    {
      "id": "chunk_probability_001",
      "content": "Probability theory and statistics fundamentals",
      "subject": "Mathematics",
      "concept": "Probability",
      "depth": 2
    }
  ],
  "count": 3,
  "max_depth": 3
}
```

## Authentication Headers

All requests require authentication. Include the session cookie or use Basic auth:

**Cookie Authentication:**
```
Cookie: trac_auth=<session_token>
```

**Basic Authentication:**
```
Authorization: Basic <base64_encoded_credentials>
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Service temporarily unavailable"
}
```

## Rate Limiting

The LLM service implements circuit breaker pattern and rate limiting:
- Maximum 60 requests per minute per user
- Circuit breaker opens after 5 consecutive failures
- Automatic retry with exponential backoff for transient errors

## Testing Tips

1. **Start with simple queries** to verify connectivity
2. **Use the health endpoints** to check service status:
   - GET /api/learntrac/llm/health
   - GET /api/learntrac/vector/health
3. **Monitor the circuit breaker state** in LLM stats endpoint
4. **Test prerequisite chains** with increasing depth values
5. **Verify embeddings** are generated correctly for new chunks