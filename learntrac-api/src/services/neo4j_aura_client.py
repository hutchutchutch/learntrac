"""
Neo4j Aura client specifically for vector search with GDS library
Implements the exact specification from Task 5
"""

from neo4j import AsyncGraphDatabase
import os
import logging
from typing import List, Dict, Any, Optional
import hashlib
import json

from ..config import settings

logger = logging.getLogger(__name__)


class Neo4jAuraClient:
    """Neo4j Aura client for vector similarity search using GDS library"""
    
    def __init__(self):
        """Initialize Neo4j driver with environment variables"""
        self.driver = None
        if settings.neo4j_uri:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50
            )
            logger.info("Neo4j Aura client initialized")
        else:
            logger.warning("Neo4j URI not configured")
    
    async def vector_search(
        self, 
        embedding: List[float], 
        min_score: float = 0.65, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on Chunk nodes
        
        Args:
            embedding: Query embedding vector
            min_score: Minimum cosine similarity score (default: 0.65)
            limit: Maximum number of results (default: 20)
            
        Returns:
            List of chunks with similarity scores
        """
        if not self.driver:
            logger.error("Neo4j driver not initialized")
            return []
        
        async with self.driver.session() as session:
            try:
                result = await session.run("""
                    MATCH (c:Chunk)
                    WITH c, gds.similarity.cosine(c.embedding, $embedding) AS score
                    WHERE score >= $min_score
                    RETURN c.id AS id, 
                           c.content AS content, 
                           c.subject AS subject, 
                           c.concept AS concept,
                           c.has_prerequisite AS has_prerequisite, 
                           c.prerequisite_for AS prerequisite_for, 
                           score
                    ORDER BY score DESC
                    LIMIT $limit
                """, embedding=embedding, min_score=min_score, limit=limit)
                
                return [record.data() async for record in result]
                
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                return []
    
    async def create_chunk(
        self,
        chunk_id: str,
        content: str,
        embedding: List[float],
        subject: Optional[str] = None,
        concept: Optional[str] = None,
        has_prerequisite: Optional[List[str]] = None,
        prerequisite_for: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create or update a Chunk node with embedding"""
        if not self.driver:
            return False
        
        async with self.driver.session() as session:
            try:
                await session.run("""
                    MERGE (c:Chunk {id: $id})
                    SET c.content = $content,
                        c.embedding = $embedding,
                        c.subject = $subject,
                        c.concept = $concept,
                        c.has_prerequisite = $has_prerequisite,
                        c.prerequisite_for = $prerequisite_for,
                        c.metadata = $metadata,
                        c.updated_at = datetime()
                """, id=chunk_id, content=content, embedding=embedding,
                    subject=subject, concept=concept,
                    has_prerequisite=has_prerequisite or [],
                    prerequisite_for=prerequisite_for or [],
                    metadata=metadata or {})
                return True
            except Exception as e:
                logger.error(f"Failed to create chunk: {e}")
                return False
    
    async def get_prerequisite_chain(
        self, 
        chunk_id: str, 
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Get all prerequisites for a chunk recursively"""
        if not self.driver:
            return []
        
        async with self.driver.session() as session:
            try:
                result = await session.run("""
                    MATCH (start:Chunk {id: $chunk_id})
                    OPTIONAL MATCH path = (start)-[:HAS_PREREQUISITE*1..%d]->(prereq:Chunk)
                    WITH DISTINCT prereq, length(path) as depth
                    WHERE prereq IS NOT NULL
                    RETURN prereq.id AS id,
                           prereq.content AS content,
                           prereq.subject AS subject,
                           prereq.concept AS concept,
                           depth
                    ORDER BY depth, prereq.id
                """ % max_depth, chunk_id=chunk_id)
                
                return [record.data() async for record in result]
                
            except Exception as e:
                logger.error(f"Failed to get prerequisite chain: {e}")
                return []
    
    async def get_dependent_concepts(
        self, 
        chunk_id: str, 
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Get all concepts that depend on this chunk"""
        if not self.driver:
            return []
        
        async with self.driver.session() as session:
            try:
                result = await session.run("""
                    MATCH (start:Chunk {id: $chunk_id})
                    OPTIONAL MATCH path = (start)<-[:HAS_PREREQUISITE*1..%d]-(dependent:Chunk)
                    WITH DISTINCT dependent, length(path) as depth
                    WHERE dependent IS NOT NULL
                    RETURN dependent.id AS id,
                           dependent.content AS content,
                           dependent.subject AS subject,
                           dependent.concept AS concept,
                           depth
                    ORDER BY depth, dependent.id
                """ % max_depth, chunk_id=chunk_id)
                
                return [record.data() async for record in result]
                
            except Exception as e:
                logger.error(f"Failed to get dependent concepts: {e}")
                return []
    
    async def create_prerequisite_relationship(
        self,
        from_chunk_id: str,
        to_chunk_id: str,
        relationship_type: str = "STRONG"
    ) -> bool:
        """Create HAS_PREREQUISITE relationship between chunks"""
        if not self.driver:
            return False
        
        async with self.driver.session() as session:
            try:
                await session.run("""
                    MATCH (from:Chunk {id: $from_id})
                    MATCH (to:Chunk {id: $to_id})
                    MERGE (from)-[r:HAS_PREREQUISITE]->(to)
                    SET r.type = $type,
                        r.created_at = coalesce(r.created_at, datetime()),
                        r.updated_at = datetime()
                """, from_id=from_chunk_id, to_id=to_chunk_id, type=relationship_type)
                
                # Update the has_prerequisite array on the from chunk
                await session.run("""
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (c)-[:HAS_PREREQUISITE]->(prereq:Chunk)
                    WITH c, collect(DISTINCT prereq.id) AS prereqs
                    SET c.has_prerequisite = prereqs
                """, chunk_id=from_chunk_id)
                
                # Update the prerequisite_for array on the to chunk
                await session.run("""
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (c)<-[:HAS_PREREQUISITE]-(dependent:Chunk)
                    WITH c, collect(DISTINCT dependent.id) AS dependents
                    SET c.prerequisite_for = dependents
                """, chunk_id=to_chunk_id)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to create prerequisite relationship: {e}")
                return False
    
    async def bulk_vector_search(
        self,
        embeddings: List[List[float]],
        min_score: float = 0.65,
        limit_per_query: int = 10
    ) -> List[List[Dict[str, Any]]]:
        """Perform multiple vector searches in one batch"""
        if not self.driver:
            return []
        
        results = []
        async with self.driver.session() as session:
            for embedding in embeddings:
                try:
                    result = await session.run("""
                        MATCH (c:Chunk)
                        WITH c, gds.similarity.cosine(c.embedding, $embedding) AS score
                        WHERE score >= $min_score
                        RETURN c.id AS id, 
                               c.content AS content, 
                               c.subject AS subject, 
                               c.concept AS concept,
                               score
                        ORDER BY score DESC
                        LIMIT $limit
                    """, embedding=embedding, min_score=min_score, limit=limit_per_query)
                    
                    batch_results = [record.data() async for record in result]
                    results.append(batch_results)
                    
                except Exception as e:
                    logger.error(f"Bulk search query failed: {e}")
                    results.append([])
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Neo4j connection health"""
        if not self.driver:
            return {"status": "not_configured", "message": "Neo4j URI not provided"}
        
        try:
            async with self.driver.session() as session:
                # Test basic connectivity
                result = await session.run("RETURN 1 as test, datetime() as server_time")
                record = await result.single()
                
                # Count chunks
                count_result = await session.run("MATCH (c:Chunk) RETURN count(c) as chunk_count")
                count_record = await count_result.single()
                
                # Check if GDS is available
                gds_result = await session.run("""
                    CALL gds.version()
                    YIELD version
                    RETURN version
                """)
                gds_record = await gds_result.single()
                
                return {
                    "status": "healthy",
                    "server_time": str(record["server_time"]),
                    "chunk_count": count_record["chunk_count"],
                    "gds_version": gds_record["version"] if gds_record else "not_installed"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def create_vector_index(self) -> bool:
        """Create vector index for Chunk embeddings"""
        if not self.driver:
            return False
        
        async with self.driver.session() as session:
            try:
                # Create vector index for cosine similarity
                await session.run("""
                    CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
                    FOR (c:Chunk)
                    ON (c.embedding)
                    OPTIONS {
                        indexConfig: {
                            `vector.dimensions`: 1536,
                            `vector.similarity_function`: 'cosine'
                        }
                    }
                """)
                
                # Create regular indexes for faster lookups
                await session.run("""
                    CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id)
                """)
                
                await session.run("""
                    CREATE INDEX chunk_subject IF NOT EXISTS FOR (c:Chunk) ON (c.subject)
                """)
                
                await session.run("""
                    CREATE INDEX chunk_concept IF NOT EXISTS FOR (c:Chunk) ON (c.concept)
                """)
                
                logger.info("Vector and lookup indexes created successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create indexes: {e}")
                return False
    
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get chunk data by ID
        
        Args:
            chunk_id: The chunk ID to retrieve
            
        Returns:
            Dict containing chunk data or None if not found
        """
        if not self.driver:
            return None
        
        async with self.driver.session() as session:
            try:
                result = await session.run("""
                    MATCH (c:Chunk {id: $chunk_id})
                    RETURN c.id AS id,
                           c.content AS content,
                           c.subject AS subject,
                           c.concept AS concept,
                           c.embedding AS embedding,
                           c.has_prerequisite AS has_prerequisite,
                           c.prerequisite_for AS prerequisite_for,
                           c.metadata AS metadata,
                           c.updated_at AS updated_at
                """, chunk_id=chunk_id)
                
                record = await result.single()
                if record:
                    return record.data()
                return None
                
            except Exception as e:
                logger.error(f"Failed to get chunk by ID {chunk_id}: {e}")
                return None
    
    async def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")


# Create singleton instance
neo4j_aura_client = Neo4jAuraClient()