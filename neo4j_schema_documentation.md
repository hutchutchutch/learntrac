# Neo4j Database Schema Documentation

## Overview
The Neo4j database stores educational textbook content in a hierarchical graph structure that preserves the natural organization of academic materials while enabling efficient searching and traversal.

## Node Types

### 1. Textbook Node
**Label**: `Textbook`

**Properties**:
- `textbook_id` (String): Unique identifier for the textbook (e.g., "cs_textbook_f4e2271b")
- `title` (String): Full title of the textbook
- `subject` (String): Subject area (e.g., "Computer Science")
- `processed_date` (DateTime): When the textbook was processed
- `total_chapters` (Integer): Number of chapters in the textbook
- `total_chunks` (Integer): Total number of text chunks created
- `authors` (Array<String>): List of authors (optional)
- `source_file` (String): Original PDF filename

**Example**:
```cypher
(:Textbook {
  textbook_id: "cs_textbook_f4e2271b",
  title: "Introduction to Computer Science",
  subject: "Computer Science",
  total_chapters: 14,
  processed_date: "2024-12-27T23:54:00Z"
})
```

### 2. Chapter Node
**Label**: `Chapter`

**Properties**:
- `textbook_id` (String): Reference to parent textbook
- `chapter_number` (Integer): Chapter number (1, 2, 3, etc.)
- `title` (String): Chapter title
- `start_page` (Integer): Starting page number in PDF
- `end_page` (Integer): Ending page number in PDF

**Example**:
```cypher
(:Chapter {
  textbook_id: "cs_textbook_f4e2271b",
  chapter_number: 1,
  title: "Introduction to Computer Science",
  start_page: 19,
  end_page: 49
})
```

### 3. Section Node
**Label**: `Section`

**Properties**:
- `textbook_id` (String): Reference to parent textbook
- `section_number` (String): Hierarchical section number (e.g., "1.1", "2.3.4")
- `title` (String): Section title
- `chapter_number` (Integer): Parent chapter number

**Example**:
```cypher
(:Section {
  textbook_id: "cs_textbook_f4e2271b",
  section_number: "1.1",
  title: "Computer Science",
  chapter_number: 1
})
```

### 4. Concept Node
**Label**: `Concept`

**Properties**:
- `textbook_id` (String): Reference to parent textbook
- `section_number` (String): Parent section number
- `concept_name` (String): Name/title of the concept
- `content_preview` (String): First 200 characters of concept content

**Example**:
```cypher
(:Concept {
  textbook_id: "cs_textbook_f4e2271b",
  section_number: "3.2",
  concept_name: "Definition: Algorithm",
  content_preview: "An algorithm is a step-by-step procedure..."
})
```

### 5. Chunk Node
**Label**: `Chunk`

**Properties**:
- `chunk_id` (String): Unique identifier (e.g., "cs_textbook_f4e2271b_ch1_s1.1_chunk0")
- `textbook_id` (String): Reference to parent textbook
- `chapter_number` (Integer): Parent chapter number
- `section_number` (String): Parent section number
- `concept_name` (String, optional): Associated concept if applicable
- `text` (String): The actual text content (500-1500 characters)
- `embedding` (Array<Float>, optional): Vector embedding for similarity search (1536 dimensions)
- `position` (Integer): Position within the source content

**Example**:
```cypher
(:Chunk {
  chunk_id: "cs_textbook_f4e2271b_ch1_s1.1_chunk0",
  textbook_id: "cs_textbook_f4e2271b",
  chapter_number: 1,
  section_number: "1.1",
  text: "Computer Science is the study of...",
  position: 0
})
```

## Relationship Types

### 1. HAS_CHAPTER
**Direction**: `(Textbook)-[:HAS_CHAPTER]->(Chapter)`

**Meaning**: A textbook contains multiple chapters

**Cardinality**: One-to-many

### 2. HAS_SECTION
**Direction**: `(Chapter)-[:HAS_SECTION]->(Section)`

**Meaning**: A chapter contains multiple sections

**Cardinality**: One-to-many

### 3. CONTAINS_CONCEPT
**Direction**: `(Section)-[:CONTAINS_CONCEPT]->(Concept)`

**Meaning**: A section contains multiple concepts/definitions

**Cardinality**: One-to-many

### 4. BELONGS_TO
**Direction**: `(Chunk)-[:BELONGS_TO]->(Section)` or `(Chunk)-[:BELONGS_TO]->(Concept)`

**Meaning**: A chunk belongs to a section or concept

**Cardinality**: Many-to-one

### 5. PRECEDES
**Direction**: `(Chapter)-[:PRECEDES]->(Chapter)`

**Meaning**: Sequential ordering between chapters (Chapter 1 PRECEDES Chapter 2)

**Cardinality**: One-to-one

### 6. NEXT
**Direction**: `(Section)-[:NEXT]->(Section)` or `(Concept)-[:NEXT]->(Concept)` or `(Chunk)-[:NEXT]->(Chunk)`

**Meaning**: Sequential ordering between elements of the same type

**Cardinality**: One-to-one

### 7. MENTIONS_CONCEPT (Optional)
**Direction**: `(Chunk)-[:MENTIONS_CONCEPT]->(Concept)`

**Meaning**: A chunk mentions or references a concept

**Cardinality**: Many-to-many

## Visual Graph Structure

```
                            Textbook
                               |
                    HAS_CHAPTER (1:many)
                               |
                            Chapter
                         /     |     \
                PRECEDES   HAS_SECTION  PRECEDES
               (to next)   (1:many)    (from prev)
                               |
                            Section
                         /     |     \
                    NEXT  CONTAINS_CONCEPT  NEXT
               (to next)    (1:many)    (from prev)
                               |
                            Concept
                         /     |     \
                    NEXT   BELONGS_TO   NEXT
               (to next)   (from chunks) (from prev)
                               |
                             Chunk
                         /     |     \
                    NEXT   BELONGS_TO   embedding[]
               (to next)   (to section)
```

## Query Examples

### 1. Get all chapters in order:
```cypher
MATCH (t:Textbook {textbook_id: $id})-[:HAS_CHAPTER]->(c:Chapter)
RETURN c ORDER BY c.chapter_number
```

### 2. Navigate chapter sequence:
```cypher
MATCH path = (c1:Chapter {chapter_number: 1})-[:PRECEDES*]->(c2:Chapter)
WHERE c1.textbook_id = $id
RETURN path
```

### 3. Get all content for a chapter:
```cypher
MATCH (c:Chapter {textbook_id: $id, chapter_number: $chapter})
      -[:HAS_SECTION]->(s:Section)
OPTIONAL MATCH (s)-[:CONTAINS_CONCEPT]->(co:Concept)
OPTIONAL MATCH (ch:Chunk)-[:BELONGS_TO]->(s)
RETURN c, s, co, ch
```

### 4. Find concepts across the textbook:
```cypher
MATCH (co:Concept {textbook_id: $id})
WHERE co.concept_name CONTAINS "Algorithm"
MATCH (co)<-[:CONTAINS_CONCEPT]-(s:Section)<-[:HAS_SECTION]-(c:Chapter)
RETURN c.chapter_number, s.section_number, co.concept_name
```

### 5. Vector similarity search (when embeddings are available):
```cypher
MATCH (c:Chunk {textbook_id: $id})
WHERE c.embedding IS NOT NULL
WITH c, gds.similarity.cosine(c.embedding, $queryEmbedding) AS similarity
WHERE similarity > 0.8
RETURN c.text, similarity
ORDER BY similarity DESC
LIMIT 10
```

### 6. Get reading path through sequential sections:
```cypher
MATCH (s1:Section {textbook_id: $id, section_number: "1.1"})
MATCH path = (s1)-[:NEXT*]->(s2:Section)
RETURN [node in nodes(path) | node.section_number] as reading_order
```

## Indexing Strategy

### Recommended Indexes:
1. **Unique constraint on Textbook**: `CREATE CONSTRAINT ON (t:Textbook) ASSERT t.textbook_id IS UNIQUE`
2. **Index on Chapter**: `CREATE INDEX ON :Chapter(textbook_id, chapter_number)`
3. **Index on Section**: `CREATE INDEX ON :Section(textbook_id, section_number)`
4. **Index on Concept**: `CREATE INDEX ON :Concept(textbook_id, concept_name)`
5. **Index on Chunk**: `CREATE INDEX ON :Chunk(textbook_id, chunk_id)`
6. **Vector index on embeddings**: `CREATE VECTOR INDEX chunk_embeddings FOR (c:Chunk) ON c.embedding`

## Benefits of This Structure

1. **Natural Hierarchy**: Preserves the textbook's original structure
2. **Flexible Navigation**: Can traverse by hierarchy or sequence
3. **Granular Access**: Can query at any level (chapter, section, concept, chunk)
4. **Semantic Search**: Chunks can be searched by content or embeddings
5. **Relationship-Rich**: Multiple relationship types enable complex queries
6. **Scalable**: Can handle multiple textbooks in the same database
7. **Educational Context**: Maintains pedagogical structure (concepts within sections)

## Usage Patterns

### For Learning Applications:
- Navigate through content sequentially using PRECEDES/NEXT
- Jump to specific concepts using direct queries
- Find related content across chapters

### For Search Applications:
- Vector similarity search on chunk embeddings
- Full-text search on chunk content
- Concept-based navigation

### For Analytics:
- Analyze concept distribution across chapters
- Track reading paths
- Identify concept relationships