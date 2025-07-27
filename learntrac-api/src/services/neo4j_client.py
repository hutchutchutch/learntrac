"""
Neo4j Aura async client for vector storage and graph operations
Handles academic content embeddings and similarity search
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class Neo4jVectorStore:
    """Neo4j client for vector storage and similarity search"""
    
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        if not settings.neo4j_uri:
            logger.warning("Neo4j URI not configured, vector features will be disabled")
            return
        
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            
            # Verify connection
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            # Create indexes if they don't exist
            await self._create_indexes()
            
            self._initialized = True
            logger.info("Neo4j connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    async def _create_indexes(self):
        """Create necessary indexes and constraints"""
        async with self.driver.session() as session:
            # Neo4j 5.12 doesn't support CREATE VECTOR INDEX syntax
            # Instead, create regular indexes for performance
            # Vector similarity search will be handled differently
            
            try:
                # Try to create constraint for unique content IDs
                await session.run("""
                    CREATE CONSTRAINT unique_content_id IF NOT EXISTS
                    FOR (c:Content)
                    REQUIRE c.content_id IS UNIQUE
                """)
            except Exception as e:
                # If constraint fails because index exists, that's ok
                logger.warning(f"Constraint creation failed (may already exist): {e}")
                
                # Try to create just the index instead
                try:
                    await session.run("""
                        CREATE INDEX content_id_index IF NOT EXISTS
                        FOR (c:Content)
                        ON (c.content_id)
                    """)
                except Exception as e2:
                    logger.info(f"Index may already exist: {e2}")
            
            # Create index for ticket references
            try:
                await session.run("""
                    CREATE INDEX content_ticket_id IF NOT EXISTS
                    FOR (c:Content)
                    ON (c.ticket_id)
                """)
            except Exception as e:
                logger.info(f"Ticket index may already exist: {e}")
    
    async def store_content_embedding(
        self,
        content_id: str,
        content_type: str,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Store content with its embedding vector"""
        if not self._initialized:
            logger.warning("Neo4j not initialized, skipping embedding storage")
            return False
        
        try:
            async with self.driver.session() as session:
                await session.run("""
                    MERGE (c:Content {content_id: $content_id})
                    SET c.content_type = $content_type,
                        c.text = $text,
                        c.embedding = $embedding,
                        c.ticket_id = $ticket_id,
                        c.concept_id = $concept_id,
                        c.created_at = datetime(),
                        c.metadata = $metadata
                """, {
                    "content_id": content_id,
                    "content_type": content_type,
                    "text": text,
                    "embedding": embedding,
                    "ticket_id": metadata.get("ticket_id"),
                    "concept_id": metadata.get("concept_id"),
                    "metadata": metadata
                })
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            return False
    
    async def find_similar_content(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.8,
        content_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar content using vector similarity search"""
        if not self._initialized:
            return []
        
        try:
            async with self.driver.session() as session:
                # Neo4j 5.12 approach: Retrieve nodes and calculate similarity in-memory
                # This is a temporary solution until vector index support is available
                
                # First, get all content nodes with embeddings
                base_query = """
                    MATCH (c:Content)
                    WHERE c.embedding IS NOT NULL
                """
                
                if content_type:
                    base_query += " AND c.content_type = $content_type"
                
                base_query += """
                    RETURN c.content_id as content_id,
                           c.content_type as content_type,
                           c.text as text,
                           c.ticket_id as ticket_id,
                           c.concept_id as concept_id,
                           c.metadata as metadata,
                           c.embedding as embedding
                """
                
                result = await session.run(base_query, {"content_type": content_type})
                
                # Calculate cosine similarity for each content
                # Using pure Python instead of numpy for compatibility
                def cosine_similarity(vec1, vec2):
                    """Calculate cosine similarity between two vectors"""
                    dot_product = sum(a * b for a, b in zip(vec1, vec2))
                    norm1 = (sum(a * a for a in vec1)) ** 0.5
                    norm2 = (sum(b * b for b in vec2)) ** 0.5
                    
                    if norm1 > 0 and norm2 > 0:
                        return dot_product / (norm1 * norm2)
                    return 0.0
                
                similar_content = []
                async for record in result:
                    content_embedding = record["embedding"]
                    if content_embedding and len(content_embedding) == len(query_embedding):
                        score = cosine_similarity(query_embedding, content_embedding)
                        
                        if score >= threshold:
                            similar_content.append({
                                "content_id": record["content_id"],
                                "content_type": record["content_type"],
                                "text": record["text"],
                                "ticket_id": record["ticket_id"],
                                "concept_id": record["concept_id"],
                                "metadata": record["metadata"],
                                "score": float(score)
                            })
                
                # Sort by score and limit results
                similar_content.sort(key=lambda x: x["score"], reverse=True)
                return similar_content[:limit]
                
        except Exception as e:
            logger.error(f"Failed to find similar content: {e}")
            return []
    
    async def create_concept_relationship(
        self,
        from_concept_id: str,
        to_concept_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create relationship between concepts in the graph"""
        if not self._initialized:
            return False
        
        try:
            async with self.driver.session() as session:
                query = f"""
                    MATCH (from:Content {{concept_id: $from_id}})
                    MATCH (to:Content {{concept_id: $to_id}})
                    MERGE (from)-[r:{relationship_type}]->(to)
                    SET r += $properties
                    SET r.created_at = datetime()
                """
                
                await session.run(query, {
                    "from_id": from_concept_id,
                    "to_id": to_concept_id,
                    "properties": properties or {}
                })
            return True
            
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
    
    async def get_concept_graph(
        self,
        concept_id: str,
        depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get concept and its related concepts up to specified depth"""
        if not self._initialized:
            return {"nodes": [], "relationships": []}
        
        try:
            async with self.driver.session() as session:
                # Build relationship filter
                rel_filter = ""
                if relationship_types:
                    rel_types = "|".join(relationship_types)
                    rel_filter = f":{rel_types}"
                
                query = f"""
                    MATCH path = (start:Content {{concept_id: $concept_id}})-[r{rel_filter}*0..{depth}]-(connected)
                    WITH collect(distinct start) + collect(distinct connected) as nodes,
                         collect(distinct r) as relationships
                    RETURN nodes, relationships
                """
                
                result = await session.run(query, {"concept_id": concept_id})
                record = await result.single()
                
                if not record:
                    return {"nodes": [], "relationships": []}
                
                # Format nodes and relationships for response
                nodes = []
                for node in record["nodes"]:
                    nodes.append({
                        "content_id": node.get("content_id"),
                        "concept_id": node.get("concept_id"),
                        "content_type": node.get("content_type"),
                        "text": node.get("text"),
                        "ticket_id": node.get("ticket_id")
                    })
                
                relationships = []
                for rel_list in record["relationships"]:
                    if rel_list:  # Check if not empty
                        for rel in rel_list:
                            relationships.append({
                                "type": type(rel).__name__,
                                "properties": dict(rel)
                            })
                
                return {
                    "nodes": nodes,
                    "relationships": relationships
                }
                
        except Exception as e:
            logger.error(f"Failed to get concept graph: {e}")
            return {"nodes": [], "relationships": []}
    
    async def delete_content(self, content_id: str) -> bool:
        """Delete content node and its relationships"""
        if not self._initialized:
            return False
        
        try:
            async with self.driver.session() as session:
                await session.run("""
                    MATCH (c:Content {content_id: $content_id})
                    DETACH DELETE c
                """, {"content_id": content_id})
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete content: {e}")
            return False


# Create singleton instance
neo4j_client = Neo4jVectorStore()