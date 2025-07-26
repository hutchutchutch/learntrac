# Neo4j Schema Design for Educational Content

## Overview

This document defines the Neo4j graph database schema for storing and querying educational content from textbooks. The schema is designed to support:

1. Hierarchical textbook structure (books → chapters → sections → chunks)
2. Vector embeddings for semantic search
3. Educational concepts and their relationships
4. Content quality and metadata tracking
5. Learning paths and prerequisites

## Node Types

### 1. Textbook
The root node representing an entire textbook.

```cypher
(:Textbook {
    textbook_id: String,      // Unique identifier
    title: String,            // Book title
    subject: String,          // Subject area (e.g., "Computer Science")
    authors: [String],        // List of authors
    isbn: String,             // ISBN if available
    publisher: String,        // Publisher name
    publication_year: Integer,// Year of publication
    language: String,         // Language code (e.g., "en")
    difficulty_level: String, // Overall difficulty (beginner/intermediate/advanced)
    
    // Processing metadata
    source_file: String,      // Original PDF file path
    processing_date: DateTime,// When processed
    processing_version: String,// Pipeline version used
    
    // Quality metrics
    extraction_confidence: Float,    // PDF extraction quality (0-1)
    structure_quality: Float,        // Structure detection quality (0-1)
    content_coherence: Float,        // Content coherence score (0-1)
    overall_quality: Float,          // Overall quality score (0-1)
    
    // Statistics
    total_chapters: Integer,
    total_sections: Integer,
    total_chunks: Integer,
    total_words: Integer,
    total_pages: Integer
})
```

### 2. Chapter
Represents a chapter within a textbook.

```cypher
(:Chapter {
    chapter_id: String,       // Unique identifier
    chapter_number: Integer,  // Chapter number
    title: String,            // Chapter title
    
    // Position in document
    start_position: Integer,  // Character position in text
    end_position: Integer,
    page_start: Integer,      // Starting page number
    page_end: Integer,        // Ending page number
    
    // Content metadata
    keywords: [String],       // Key terms in chapter
    topics: [String],         // Main topics covered
    learning_objectives: [String], // Learning goals
    
    // Statistics
    word_count: Integer,
    section_count: Integer,
    chunk_count: Integer
})
```

### 3. Section
Represents a section within a chapter.

```cypher
(:Section {
    section_id: String,       // Unique identifier
    section_number: String,   // Section number (e.g., "2.1", "2.1.1")
    title: String,            // Section title
    level: Integer,           // Nesting level (1, 2, 3...)
    
    // Position in document
    start_position: Integer,
    end_position: Integer,
    
    // Content metadata
    keywords: [String],
    topics: [String],
    
    // Statistics
    word_count: Integer,
    chunk_count: Integer
})
```

### 4. Chunk
The smallest unit of content, optimized for embedding and retrieval.

```cypher
(:Chunk {
    chunk_id: String,         // Unique identifier
    content_type: String,     // text/math/definition/example/code/etc.
    text: String,             // The actual text content
    
    // Embedding - stored as property for vector index
    embedding: [Float],       // Vector embedding (384-3072 dimensions)
    embedding_model: String,  // Model used for embedding
    embedding_dimensions: Integer,
    
    // Position in document
    start_position: Integer,
    end_position: Integer,
    page_numbers: [Integer],  // Pages this chunk spans
    
    // Educational metadata
    difficulty_score: Float,  // 0-1 difficulty rating
    concepts: [String],       // Concepts mentioned
    prerequisites: [String],  // Required prior knowledge
    
    // Quality metrics
    confidence_score: Float,  // Extraction confidence
    coherence_score: Float,   // Content coherence
    quality_score: Float,     // Overall quality
    
    // Processing metadata
    chunking_strategy: String,// "content_aware" or "fallback"
    created_at: DateTime,
    
    // Statistics
    char_count: Integer,
    word_count: Integer,
    sentence_count: Integer
})
```

### 5. Concept
Educational concepts extracted from content.

```cypher
(:Concept {
    concept_id: String,       // Unique identifier
    name: String,             // Concept name
    type: String,             // definition/theorem/algorithm/principle
    
    // Educational metadata
    subject_area: String,     // Primary subject
    difficulty_level: String, // Difficulty rating
    importance_score: Float,  // How important this concept is
    
    // Content
    definition: String,       // Formal definition if available
    description: String,      // Detailed description
    examples: [String],       // Example applications
    
    // Relationships tracking
    prerequisite_count: Integer,
    dependent_count: Integer,
    reference_count: Integer  // How often referenced
})
```

### 6. LearningPath
Curated sequences of content for learning.

```cypher
(:LearningPath {
    path_id: String,          // Unique identifier
    title: String,            // Path title
    description: String,      // Path description
    
    // Educational metadata
    target_audience: String,  // Who this is for
    difficulty_level: String,
    estimated_hours: Integer,
    
    // Content
    learning_objectives: [String],
    prerequisites: [String],
    
    // Statistics
    total_concepts: Integer,
    total_chunks: Integer,
    
    // Metadata
    created_by: String,
    created_at: DateTime,
    updated_at: DateTime
})
```

## Relationship Types

### 1. Structural Relationships

```cypher
// Book structure
(textbook:Textbook)-[:HAS_CHAPTER]->(chapter:Chapter)
(chapter:Chapter)-[:HAS_SECTION]->(section:Section)
(section:Section)-[:HAS_CHUNK]->(chunk:Chunk)

// Direct parent relationships for chunks
(chunk:Chunk)-[:BELONGS_TO_SECTION]->(section:Section)
(chunk:Chunk)-[:BELONGS_TO_CHAPTER]->(chapter:Chapter)
(chunk:Chunk)-[:BELONGS_TO_TEXTBOOK]->(textbook:Textbook)

// Sequential relationships
(chunk1:Chunk)-[:NEXT]->(chunk2:Chunk)
(section1:Section)-[:NEXT]->(section2:Section)
(chapter1:Chapter)-[:NEXT]->(chapter2:Chapter)
```

### 2. Educational Relationships

```cypher
// Concept relationships
(chunk:Chunk)-[:INTRODUCES_CONCEPT]->(concept:Concept)
(chunk:Chunk)-[:EXPLAINS_CONCEPT]->(concept:Concept)
(chunk:Chunk)-[:USES_CONCEPT]->(concept:Concept)

// Prerequisite relationships
(concept1:Concept)-[:REQUIRES]->(concept2:Concept)
(chunk:Chunk)-[:REQUIRES_CONCEPT]->(concept:Concept)
(section:Section)-[:REQUIRES_CONCEPT]->(concept:Concept)

// Learning path relationships
(path:LearningPath)-[:INCLUDES_CONCEPT {order: Integer}]->(concept:Concept)
(path:LearningPath)-[:INCLUDES_CHUNK {order: Integer}]->(chunk:Chunk)
(path:LearningPath)-[:STARTS_WITH]->(chunk:Chunk)
```

### 3. Similarity Relationships

```cypher
// Content similarity (computed from embeddings)
(chunk1:Chunk)-[:SIMILAR_TO {similarity: Float}]->(chunk2:Chunk)

// Concept similarity
(concept1:Concept)-[:RELATED_TO {strength: Float}]->(concept2:Concept)
```

## Indexes and Constraints

### Vector Indexes

```cypher
// Vector index for chunk embeddings
CREATE VECTOR INDEX chunkEmbedding IF NOT EXISTS
FOR (c:Chunk)
ON c.embedding
OPTIONS {
    indexConfig: {
        `vector.dimensions`: 768,  // Adjust based on model
        `vector.similarity_function`: 'cosine'
    }
}
```

### Unique Constraints

```cypher
// Unique identifiers
CREATE CONSTRAINT unique_textbook_id IF NOT EXISTS
FOR (t:Textbook) REQUIRE t.textbook_id IS UNIQUE;

CREATE CONSTRAINT unique_chapter_id IF NOT EXISTS
FOR (c:Chapter) REQUIRE c.chapter_id IS UNIQUE;

CREATE CONSTRAINT unique_section_id IF NOT EXISTS
FOR (s:Section) REQUIRE s.section_id IS UNIQUE;

CREATE CONSTRAINT unique_chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT unique_concept_id IF NOT EXISTS
FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE;

CREATE CONSTRAINT unique_path_id IF NOT EXISTS
FOR (p:LearningPath) REQUIRE p.path_id IS UNIQUE;
```

### Property Indexes

```cypher
// Performance indexes
CREATE INDEX textbook_subject IF NOT EXISTS
FOR (t:Textbook) ON (t.subject);

CREATE INDEX chunk_content_type IF NOT EXISTS
FOR (c:Chunk) ON (c.content_type);

CREATE INDEX chunk_difficulty IF NOT EXISTS
FOR (c:Chunk) ON (c.difficulty_score);

CREATE INDEX concept_name IF NOT EXISTS
FOR (c:Concept) ON (c.name);

CREATE INDEX concept_type IF NOT EXISTS
FOR (c:Concept) ON (c.type);
```

## Query Examples

### 1. Find similar chunks
```cypher
MATCH (query:Chunk {chunk_id: $chunk_id})
CALL db.index.vector.queryNodes('chunkEmbedding', 10, query.embedding)
YIELD node, score
WHERE score > 0.8 AND node.chunk_id <> $chunk_id
RETURN node, score
ORDER BY score DESC
```

### 2. Get learning path for a concept
```cypher
MATCH (c:Concept {name: $concept_name})
MATCH path = (c)<-[:REQUIRES*]-(dependent:Concept)
RETURN path
ORDER BY length(path) DESC
```

### 3. Find all content for a topic
```cypher
MATCH (chunk:Chunk)-[:BELONGS_TO_TEXTBOOK]->(book:Textbook)
WHERE $topic IN chunk.topics
RETURN book.title, chunk.text, chunk.difficulty_score
ORDER BY chunk.difficulty_score ASC
```

### 4. Get chapter with all its content
```cypher
MATCH (chapter:Chapter {chapter_id: $chapter_id})
MATCH (chapter)-[:HAS_SECTION]->(section:Section)
MATCH (section)-[:HAS_CHUNK]->(chunk:Chunk)
RETURN chapter, section, chunk
ORDER BY section.section_number, chunk.start_position
```

## Migration from Existing Schema

The existing schema uses a simpler structure:
- `Content` nodes with embeddings
- Basic metadata

Migration steps:
1. Transform existing `Content` nodes to `Chunk` nodes
2. Extract textbook/chapter/section structure from metadata
3. Create hierarchical relationships
4. Extract and link concepts
5. Rebuild vector indexes with new schema

## Performance Considerations

1. **Denormalization**: Some relationships are denormalized (e.g., chunk directly to textbook) for query performance
2. **Batch Processing**: Ingestion should be done in batches of 1000-5000 nodes
3. **Embedding Storage**: Consider using compressed embeddings for large datasets
4. **Relationship Limits**: Limit SIMILAR_TO relationships to top-k most similar
5. **Caching**: Frequently accessed paths should be cached in application layer