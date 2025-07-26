"""
Neo4j Vector Index Manager for Educational Content

Manages vector indexes in Neo4j including:
- Index creation and configuration
- Index maintenance and optimization
- Vector similarity search
- Index statistics and monitoring
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig

logger = logging.getLogger(__name__)


class VectorSimilarityFunction(Enum):
    """Supported vector similarity functions"""
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot-product"


class IndexStatus(Enum):
    """Vector index status"""
    ONLINE = "online"
    POPULATING = "populating"
    FAILED = "failed"
    NOT_EXISTS = "not_exists"


@dataclass
class VectorIndexConfig:
    """Configuration for a vector index"""
    index_name: str
    node_label: str
    property_name: str
    dimensions: int
    similarity_function: VectorSimilarityFunction = VectorSimilarityFunction.COSINE
    
    # Advanced settings
    m: int = 16  # Number of neighbors in HNSW graph
    ef_construction: int = 200  # Size of dynamic candidate list
    ef_search: int = 50  # Size of candidate list for search
    
    def to_cypher_options(self) -> Dict[str, Any]:
        """Convert to Cypher OPTIONS format"""
        return {
            "indexConfig": {
                "vector.dimensions": self.dimensions,
                "vector.similarity_function": self.similarity_function.value,
                "vector.hnsw.m": self.m,
                "vector.hnsw.ef_construction": self.ef_construction
            }
        }


@dataclass
class VectorIndexInfo:
    """Information about a vector index"""
    name: str
    state: str
    node_label: str
    property_name: str
    dimensions: Optional[int]
    similarity_function: Optional[str]
    entity_count: Optional[int]
    index_size: Optional[int]
    created_time: Optional[datetime]
    last_updated: Optional[datetime]


@dataclass
class VectorSearchResult:
    """Result from vector similarity search"""
    node_id: str
    score: float
    node_properties: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class Neo4jVectorIndexManager:
    """
    Manages Neo4j vector indexes for educational content.
    
    Features:
    - Create and configure vector indexes
    - Monitor index status and health
    - Perform vector similarity searches
    - Manage multiple indexes
    - Index optimization and maintenance
    """
    
    def __init__(self, connection_manager: Neo4jConnectionManager):
        """
        Initialize vector index manager.
        
        Args:
            connection_manager: Neo4j connection manager instance
        """
        self.connection = connection_manager
        self.index_configs: Dict[str, VectorIndexConfig] = {}
        
    async def create_index(
        self,
        config: VectorIndexConfig,
        drop_if_exists: bool = False
    ) -> bool:
        """
        Create a vector index.
        
        Args:
            config: Vector index configuration
            drop_if_exists: Drop existing index before creation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if index exists
            if await self.index_exists(config.index_name):
                if drop_if_exists:
                    logger.info(f"Dropping existing index: {config.index_name}")
                    await self.drop_index(config.index_name)
                else:
                    logger.warning(f"Index already exists: {config.index_name}")
                    return False
            
            # Create the index
            query = f"""
                CREATE VECTOR INDEX {config.index_name} IF NOT EXISTS
                FOR (n:{config.node_label})
                ON n.{config.property_name}
                OPTIONS $options
            """
            
            await self.connection.execute_query(
                query,
                {"options": config.to_cypher_options()}
            )
            
            # Store configuration
            self.index_configs[config.index_name] = config
            
            logger.info(f"Created vector index: {config.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False
    
    async def drop_index(self, index_name: str) -> bool:
        """
        Drop a vector index.
        
        Args:
            index_name: Name of the index to drop
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = f"DROP INDEX {index_name} IF EXISTS"
            await self.connection.execute_query(query)
            
            # Remove from configs
            self.index_configs.pop(index_name, None)
            
            logger.info(f"Dropped vector index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop vector index: {e}")
            return False
    
    async def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.
        
        Args:
            index_name: Name of the index
            
        Returns:
            True if exists, False otherwise
        """
        try:
            query = """
                SHOW INDEXES
                YIELD name
                WHERE name = $index_name
                RETURN count(*) > 0 as exists
            """
            
            results = await self.connection.execute_query(
                query,
                {"index_name": index_name}
            )
            
            return results[0]["exists"] if results else False
            
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False
    
    async def get_index_info(self, index_name: str) -> Optional[VectorIndexInfo]:
        """
        Get detailed information about a vector index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index information or None if not found
        """
        try:
            query = """
                SHOW INDEXES
                YIELD name, state, labelsOrTypes, properties, options, 
                      createStatement, uniqueness, type
                WHERE name = $index_name
                RETURN *
            """
            
            results = await self.connection.execute_query(
                query,
                {"index_name": index_name}
            )
            
            if not results:
                return None
            
            index_data = results[0]
            
            # Extract vector-specific options
            options = index_data.get("options", {})
            index_config = options.get("indexConfig", {})
            
            # Get entity count
            entity_count = await self._get_indexed_entity_count(
                index_data["labelsOrTypes"][0],
                index_data["properties"][0]
            )
            
            return VectorIndexInfo(
                name=index_data["name"],
                state=index_data["state"],
                node_label=index_data["labelsOrTypes"][0],
                property_name=index_data["properties"][0],
                dimensions=index_config.get("vector.dimensions"),
                similarity_function=index_config.get("vector.similarity_function"),
                entity_count=entity_count,
                index_size=None,  # Neo4j doesn't directly expose this
                created_time=None,  # Not available in standard SHOW INDEXES
                last_updated=None
            )
            
        except Exception as e:
            logger.error(f"Failed to get index info: {e}")
            return None
    
    async def list_vector_indexes(self) -> List[VectorIndexInfo]:
        """
        List all vector indexes.
        
        Returns:
            List of vector index information
        """
        try:
            query = """
                SHOW INDEXES
                WHERE type = 'VECTOR'
                YIELD name, state, labelsOrTypes, properties, options
                RETURN *
            """
            
            results = await self.connection.execute_query(query)
            
            indexes = []
            for index_data in results:
                options = index_data.get("options", {})
                index_config = options.get("indexConfig", {})
                
                entity_count = await self._get_indexed_entity_count(
                    index_data["labelsOrTypes"][0],
                    index_data["properties"][0]
                )
                
                indexes.append(VectorIndexInfo(
                    name=index_data["name"],
                    state=index_data["state"],
                    node_label=index_data["labelsOrTypes"][0],
                    property_name=index_data["properties"][0],
                    dimensions=index_config.get("vector.dimensions"),
                    similarity_function=index_config.get("vector.similarity_function"),
                    entity_count=entity_count,
                    index_size=None,
                    created_time=None,
                    last_updated=None
                ))
            
            return indexes
            
        except Exception as e:
            logger.error(f"Failed to list vector indexes: {e}")
            return []
    
    async def get_index_status(self, index_name: str) -> IndexStatus:
        """
        Get the status of a vector index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index status
        """
        try:
            info = await self.get_index_info(index_name)
            
            if not info:
                return IndexStatus.NOT_EXISTS
            
            state_map = {
                "ONLINE": IndexStatus.ONLINE,
                "POPULATING": IndexStatus.POPULATING,
                "FAILED": IndexStatus.FAILED
            }
            
            return state_map.get(info.state.upper(), IndexStatus.FAILED)
            
        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return IndexStatus.FAILED
    
    async def wait_for_index_online(
        self,
        index_name: str,
        timeout_seconds: int = 300,
        check_interval: float = 1.0
    ) -> bool:
        """
        Wait for an index to become online.
        
        Args:
            index_name: Name of the index
            timeout_seconds: Maximum wait time
            check_interval: Time between status checks
            
        Returns:
            True if index is online, False if timeout
        """
        import asyncio
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.get_index_status(index_name)
            
            if status == IndexStatus.ONLINE:
                return True
            
            if status == IndexStatus.FAILED:
                logger.error(f"Index {index_name} failed to build")
                return False
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                logger.error(f"Timeout waiting for index {index_name}")
                return False
            
            await asyncio.sleep(check_interval)
    
    async def vector_search(
        self,
        index_name: str,
        query_vector: List[float],
        limit: int = 10,
        min_score: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        return_properties: Optional[List[str]] = None
    ) -> List[VectorSearchResult]:
        """
        Perform vector similarity search.
        
        Args:
            index_name: Name of the vector index
            query_vector: Query embedding vector
            limit: Maximum number of results
            min_score: Minimum similarity score
            filters: Additional node property filters
            return_properties: Specific properties to return
            
        Returns:
            List of search results
        """
        try:
            # Get index configuration
            index_info = await self.get_index_info(index_name)
            if not index_info:
                raise ValueError(f"Index {index_name} not found")
            
            # Build the query
            query_parts = [
                f"CALL db.index.vector.queryNodes('{index_name}', $limit, $query_vector)",
                "YIELD node, score"
            ]
            
            # Add score filter
            if min_score is not None:
                query_parts.append(f"WHERE score >= {min_score}")
            
            # Add property filters
            if filters:
                filter_conditions = []
                for prop, value in filters.items():
                    if isinstance(value, str):
                        filter_conditions.append(f"node.{prop} = '{value}'")
                    else:
                        filter_conditions.append(f"node.{prop} = {value}")
                
                if filter_conditions:
                    where_clause = " AND ".join(filter_conditions)
                    if min_score is not None:
                        query_parts[-1] += f" AND {where_clause}"
                    else:
                        query_parts.append(f"WHERE {where_clause}")
            
            # Build return clause
            if return_properties:
                return_props = [f"node.{prop} as {prop}" for prop in return_properties]
                return_clause = f"RETURN id(node) as node_id, score, {', '.join(return_props)}"
            else:
                return_clause = "RETURN id(node) as node_id, score, node"
            
            query_parts.append(return_clause)
            query_parts.append("ORDER BY score DESC")
            
            query = "\n".join(query_parts)
            
            # Execute search
            results = await self.connection.execute_query(
                query,
                {
                    "query_vector": query_vector,
                    "limit": limit
                }
            )
            
            # Format results
            search_results = []
            for record in results:
                if "node" in record:
                    # Full node returned
                    node_props = dict(record["node"])
                else:
                    # Specific properties returned
                    node_props = {k: v for k, v in record.items() 
                                 if k not in ["node_id", "score"]}
                
                search_results.append(VectorSearchResult(
                    node_id=str(record["node_id"]),
                    score=record["score"],
                    node_properties=node_props
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def batch_vector_search(
        self,
        index_name: str,
        query_vectors: List[List[float]],
        limit_per_query: int = 10,
        min_score: Optional[float] = None
    ) -> List[List[VectorSearchResult]]:
        """
        Perform batch vector similarity searches.
        
        Args:
            index_name: Name of the vector index
            query_vectors: List of query embedding vectors
            limit_per_query: Maximum results per query
            min_score: Minimum similarity score
            
        Returns:
            List of search results for each query
        """
        results = []
        
        # Process in parallel using async
        import asyncio
        tasks = [
            self.vector_search(
                index_name,
                query_vector,
                limit_per_query,
                min_score
            )
            for query_vector in query_vectors
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Batch search {i} failed: {result}")
                results.append([])
            else:
                results.append(result)
        
        return results
    
    async def update_index_config(
        self,
        index_name: str,
        ef_search: Optional[int] = None
    ) -> bool:
        """
        Update index configuration (limited options available at runtime).
        
        Args:
            index_name: Name of the index
            ef_search: New ef_search value for HNSW
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if ef_search is not None:
                # Update ef_search parameter
                query = """
                    CALL db.index.vector.setConfig($index_name, 'vector.hnsw.ef_search', $ef_search)
                """
                
                await self.connection.execute_query(
                    query,
                    {
                        "index_name": index_name,
                        "ef_search": ef_search
                    }
                )
                
                logger.info(f"Updated ef_search for {index_name} to {ef_search}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update index config: {e}")
            return False
    
    async def analyze_index_distribution(
        self,
        index_name: str,
        sample_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Analyze the distribution of vectors in an index.
        
        Args:
            index_name: Name of the index
            sample_size: Number of vectors to sample
            
        Returns:
            Analysis results
        """
        try:
            # Get index info
            index_info = await self.get_index_info(index_name)
            if not index_info:
                return {"error": "Index not found"}
            
            # Sample vectors from the index
            query = f"""
                MATCH (n:{index_info.node_label})
                WHERE n.{index_info.property_name} IS NOT NULL
                WITH n LIMIT $sample_size
                WITH collect(n.{index_info.property_name}) as vectors
                RETURN vectors, size(vectors) as sample_count
            """
            
            results = await self.connection.execute_query(
                query,
                {"sample_size": sample_size}
            )
            
            if not results or not results[0]["vectors"]:
                return {"error": "No vectors found"}
            
            vectors = results[0]["vectors"]
            sample_count = results[0]["sample_count"]
            
            # Calculate statistics
            import numpy as np
            vectors_array = np.array(vectors)
            
            # Compute pairwise similarities for a subset
            subset_size = min(100, len(vectors))
            subset_vectors = vectors_array[:subset_size]
            
            similarities = []
            for i in range(subset_size):
                for j in range(i + 1, subset_size):
                    # Cosine similarity
                    sim = np.dot(subset_vectors[i], subset_vectors[j]) / (
                        np.linalg.norm(subset_vectors[i]) * np.linalg.norm(subset_vectors[j])
                    )
                    similarities.append(sim)
            
            analysis = {
                "index_name": index_name,
                "total_entities": index_info.entity_count,
                "sample_size": sample_count,
                "dimensions": index_info.dimensions,
                "vector_stats": {
                    "mean_norm": float(np.mean(np.linalg.norm(vectors_array, axis=1))),
                    "std_norm": float(np.std(np.linalg.norm(vectors_array, axis=1))),
                    "min_norm": float(np.min(np.linalg.norm(vectors_array, axis=1))),
                    "max_norm": float(np.max(np.linalg.norm(vectors_array, axis=1)))
                },
                "similarity_distribution": {
                    "mean": float(np.mean(similarities)) if similarities else 0,
                    "std": float(np.std(similarities)) if similarities else 0,
                    "min": float(np.min(similarities)) if similarities else 0,
                    "max": float(np.max(similarities)) if similarities else 0,
                    "percentiles": {
                        "25": float(np.percentile(similarities, 25)) if similarities else 0,
                        "50": float(np.percentile(similarities, 50)) if similarities else 0,
                        "75": float(np.percentile(similarities, 75)) if similarities else 0
                    }
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze index distribution: {e}")
            return {"error": str(e)}
    
    async def optimize_index(self, index_name: str) -> bool:
        """
        Optimize a vector index (trigger rebuild if needed).
        
        Args:
            index_name: Name of the index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Neo4j doesn't provide direct index optimization commands
            # But we can adjust ef_search for better recall
            current_info = await self.get_index_info(index_name)
            if not current_info:
                return False
            
            # Analyze current performance
            analysis = await self.analyze_index_distribution(index_name)
            
            # Adjust ef_search based on entity count
            entity_count = current_info.entity_count or 0
            
            if entity_count > 1000000:
                new_ef_search = 200
            elif entity_count > 100000:
                new_ef_search = 100
            else:
                new_ef_search = 50
            
            await self.update_index_config(index_name, ef_search=new_ef_search)
            
            logger.info(f"Optimized index {index_name} for {entity_count} entities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize index: {e}")
            return False
    
    async def _get_indexed_entity_count(
        self,
        node_label: str,
        property_name: str
    ) -> int:
        """
        Get count of entities with the indexed property.
        
        Args:
            node_label: Node label
            property_name: Property name
            
        Returns:
            Entity count
        """
        try:
            query = f"""
                MATCH (n:{node_label})
                WHERE n.{property_name} IS NOT NULL
                RETURN count(n) as count
            """
            
            results = await self.connection.execute_query(query)
            return results[0]["count"] if results else 0
            
        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            return 0
    
    async def create_educational_indexes(self) -> Dict[str, bool]:
        """
        Create all standard indexes for educational content.
        
        Returns:
            Dictionary of index names and creation status
        """
        indexes = [
            VectorIndexConfig(
                index_name="chunkEmbedding",
                node_label="Chunk",
                property_name="embedding",
                dimensions=768,  # Default, adjust based on model
                similarity_function=VectorSimilarityFunction.COSINE
            ),
            VectorIndexConfig(
                index_name="conceptEmbedding",
                node_label="Concept",
                property_name="embedding",
                dimensions=768,
                similarity_function=VectorSimilarityFunction.COSINE
            ),
            VectorIndexConfig(
                index_name="sectionEmbedding",
                node_label="Section",
                property_name="embedding",
                dimensions=768,
                similarity_function=VectorSimilarityFunction.COSINE
            )
        ]
        
        results = {}
        for config in indexes:
            results[config.index_name] = await self.create_index(config)
        
        return results