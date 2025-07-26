"""
Neo4j Relationship Manager for Educational Concepts

Manages complex relationships between educational content including:
- Concept hierarchies and dependencies
- Learning path construction
- Prerequisite tracking
- Content similarity relationships
- Concept evolution and versioning
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import networkx as nx
from collections import defaultdict

from .neo4j_connection_manager import Neo4jConnectionManager

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Types of relationships in educational content"""
    # Structural relationships
    HAS_CHAPTER = "HAS_CHAPTER"
    HAS_SECTION = "HAS_SECTION"
    HAS_CHUNK = "HAS_CHUNK"
    BELONGS_TO = "BELONGS_TO"
    NEXT = "NEXT"
    PREVIOUS = "PREVIOUS"
    
    # Conceptual relationships
    INTRODUCES_CONCEPT = "INTRODUCES_CONCEPT"
    EXPLAINS_CONCEPT = "EXPLAINS_CONCEPT"
    USES_CONCEPT = "USES_CONCEPT"
    MENTIONS_CONCEPT = "MENTIONS_CONCEPT"
    
    # Prerequisite relationships
    REQUIRES = "REQUIRES"
    REQUIRES_CONCEPT = "REQUIRES_CONCEPT"
    BUILDS_UPON = "BUILDS_UPON"
    PREREQUISITE_OF = "PREREQUISITE_OF"
    
    # Similarity relationships
    SIMILAR_TO = "SIMILAR_TO"
    RELATED_TO = "RELATED_TO"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    
    # Learning path relationships
    INCLUDES_CONCEPT = "INCLUDES_CONCEPT"
    INCLUDES_CHUNK = "INCLUDES_CHUNK"
    STARTS_WITH = "STARTS_WITH"
    FOLLOWED_BY = "FOLLOWED_BY"


@dataclass
class ConceptRelationship:
    """Represents a relationship between concepts"""
    source_concept: str
    target_concept: str
    relationship_type: RelationshipType
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConceptHierarchy:
    """Represents a hierarchical structure of concepts"""
    root_concepts: List[str]
    concept_tree: Dict[str, List[str]]  # parent -> children
    concept_levels: Dict[str, int]  # concept -> depth level
    total_concepts: int
    max_depth: int
    

@dataclass
class LearningPathSegment:
    """A segment in a learning path"""
    segment_id: str
    concepts: List[str]
    chunks: List[str]
    prerequisites: List[str]
    learning_objectives: List[str]
    estimated_time_minutes: int
    difficulty_level: float


@dataclass
class ConceptGraph:
    """Graph representation of concept relationships"""
    nodes: Set[str]  # Concept names
    edges: List[Tuple[str, str, Dict[str, Any]]]  # (source, target, properties)
    node_properties: Dict[str, Dict[str, Any]]
    
    def to_networkx(self) -> nx.DiGraph:
        """Convert to NetworkX graph for analysis"""
        G = nx.DiGraph()
        
        # Add nodes with properties
        for node in self.nodes:
            props = self.node_properties.get(node, {})
            G.add_node(node, **props)
        
        # Add edges with properties
        for source, target, props in self.edges:
            G.add_edge(source, target, **props)
        
        return G


class Neo4jRelationshipManager:
    """
    Manages relationships between educational content in Neo4j.
    
    Features:
    - Concept hierarchy construction
    - Prerequisite chain analysis
    - Learning path generation
    - Relationship strength calculation
    - Cycle detection and prevention
    - Concept clustering
    """
    
    def __init__(self, connection_manager: Neo4jConnectionManager):
        """
        Initialize relationship manager.
        
        Args:
            connection_manager: Neo4j connection manager
        """
        self.connection = connection_manager
        
    async def create_concept_relationship(
        self,
        source_concept: str,
        target_concept: str,
        relationship_type: RelationshipType,
        strength: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a relationship between two concepts.
        
        Args:
            source_concept: Source concept name
            target_concept: Target concept name
            relationship_type: Type of relationship
            strength: Relationship strength (0-1)
            metadata: Additional relationship properties
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prevent self-relationships
            if source_concept == target_concept:
                logger.warning(f"Cannot create self-relationship for concept: {source_concept}")
                return False
            
            # Check for cycles in prerequisite relationships
            if relationship_type in [RelationshipType.REQUIRES, RelationshipType.PREREQUISITE_OF]:
                if await self._would_create_cycle(source_concept, target_concept, relationship_type):
                    logger.warning(f"Relationship would create cycle: {source_concept} -> {target_concept}")
                    return False
            
            query = """
                MATCH (source:Concept {name: $source})
                MATCH (target:Concept {name: $target})
                MERGE (source)-[r:%s]->(target)
                SET r.strength = $strength,
                    r.created_at = datetime(),
                    r.updated_at = datetime()
            """ % relationship_type.value
            
            # Add metadata if provided
            if metadata:
                query += """
                    SET r += $metadata
                """
            
            await self.connection.execute_query(
                query,
                {
                    "source": source_concept,
                    "target": target_concept,
                    "strength": strength,
                    "metadata": metadata or {}
                }
            )
            
            logger.info(f"Created relationship: {source_concept} -{relationship_type.value}-> {target_concept}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create concept relationship: {e}")
            return False
    
    async def create_chunk_concept_relationships(
        self,
        chunk_id: str,
        concepts: List[str],
        relationship_type: RelationshipType = RelationshipType.MENTIONS_CONCEPT
    ) -> int:
        """
        Create relationships between a chunk and multiple concepts.
        
        Args:
            chunk_id: Chunk identifier
            concepts: List of concept names
            relationship_type: Type of relationship
            
        Returns:
            Number of relationships created
        """
        if not concepts:
            return 0
        
        try:
            query = """
                MATCH (chunk:Chunk {chunk_id: $chunk_id})
                UNWIND $concepts as concept_name
                MERGE (concept:Concept {name: concept_name})
                ON CREATE SET concept.concept_id = apoc.create.uuid(),
                             concept.created_at = datetime()
                MERGE (chunk)-[r:%s]->(concept)
                SET r.created_at = datetime()
                RETURN count(r) as count
            """ % relationship_type.value
            
            results = await self.connection.execute_query(
                query,
                {
                    "chunk_id": chunk_id,
                    "concepts": concepts
                }
            )
            
            count = results[0]["count"] if results else 0
            logger.info(f"Created {count} chunk-concept relationships for chunk {chunk_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to create chunk-concept relationships: {e}")
            return 0
    
    async def build_concept_hierarchy(
        self,
        subject_area: Optional[str] = None
    ) -> ConceptHierarchy:
        """
        Build a hierarchical structure of concepts.
        
        Args:
            subject_area: Optional subject filter
            
        Returns:
            Concept hierarchy structure
        """
        try:
            # Get all concept relationships
            query = """
                MATCH (c:Concept)
                WHERE $subject_area IS NULL OR c.subject_area = $subject_area
                OPTIONAL MATCH (c)-[:REQUIRES|BUILDS_UPON]->(parent:Concept)
                RETURN c.name as concept,
                       collect(distinct parent.name) as parents
            """
            
            results = await self.connection.execute_query(
                query,
                {"subject_area": subject_area}
            )
            
            # Build parent-child mappings
            concept_tree = defaultdict(list)
            concept_parents = {}
            all_concepts = set()
            
            for record in results:
                concept = record["concept"]
                parents = record["parents"]
                all_concepts.add(concept)
                
                if parents:
                    concept_parents[concept] = parents
                    for parent in parents:
                        concept_tree[parent].append(concept)
                        all_concepts.add(parent)
            
            # Find root concepts (no parents)
            root_concepts = [c for c in all_concepts if c not in concept_parents]
            
            # Calculate levels
            concept_levels = {}
            self._calculate_levels(root_concepts, concept_tree, concept_levels, 0)
            
            # Calculate max depth
            max_depth = max(concept_levels.values()) if concept_levels else 0
            
            return ConceptHierarchy(
                root_concepts=root_concepts,
                concept_tree=dict(concept_tree),
                concept_levels=concept_levels,
                total_concepts=len(all_concepts),
                max_depth=max_depth
            )
            
        except Exception as e:
            logger.error(f"Failed to build concept hierarchy: {e}")
            return ConceptHierarchy([], {}, {}, 0, 0)
    
    async def find_prerequisite_chain(
        self,
        target_concept: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        Find all prerequisite chains leading to a concept.
        
        Args:
            target_concept: Target concept
            max_depth: Maximum chain depth
            
        Returns:
            List of prerequisite chains
        """
        try:
            query = """
                MATCH path = (start:Concept)-[:REQUIRES*1..%d]->(target:Concept {name: $target})
                RETURN [n in nodes(path) | n.name] as chain
                ORDER BY length(path) DESC
                LIMIT 100
            """ % max_depth
            
            results = await self.connection.execute_query(
                query,
                {"target": target_concept}
            )
            
            chains = [record["chain"] for record in results]
            
            # Reverse chains so they start from prerequisites
            chains = [list(reversed(chain)) for chain in chains]
            
            # Remove duplicate chains
            unique_chains = []
            seen = set()
            for chain in chains:
                chain_tuple = tuple(chain)
                if chain_tuple not in seen:
                    seen.add(chain_tuple)
                    unique_chains.append(chain)
            
            return unique_chains
            
        except Exception as e:
            logger.error(f"Failed to find prerequisite chains: {e}")
            return []
    
    async def suggest_learning_path(
        self,
        target_concepts: List[str],
        user_level: str = "beginner",
        max_chunks: int = 50
    ) -> List[LearningPathSegment]:
        """
        Suggest a learning path to master target concepts.
        
        Args:
            target_concepts: Concepts to learn
            user_level: User's current level
            max_chunks: Maximum chunks in path
            
        Returns:
            Ordered learning path segments
        """
        try:
            # Find all prerequisites
            all_concepts = set(target_concepts)
            prerequisites = set()
            
            for concept in target_concepts:
                chains = await self.find_prerequisite_chain(concept)
                for chain in chains:
                    prerequisites.update(chain[:-1])  # Exclude target
            
            all_concepts.update(prerequisites)
            
            # Get chunks for each concept with difficulty
            query = """
                MATCH (concept:Concept)
                WHERE concept.name IN $concepts
                MATCH (chunk:Chunk)-[:INTRODUCES_CONCEPT|EXPLAINS_CONCEPT]->(concept)
                RETURN concept.name as concept,
                       chunk.chunk_id as chunk_id,
                       chunk.difficulty_score as difficulty,
                       chunk.content_type as content_type,
                       chunk.textbook_id as textbook_id,
                       chunk.start_position as position
                ORDER BY chunk.difficulty_score ASC, chunk.start_position ASC
            """
            
            results = await self.connection.execute_query(
                query,
                {"concepts": list(all_concepts)}
            )
            
            # Group chunks by concept
            concept_chunks = defaultdict(list)
            for record in results:
                concept_chunks[record["concept"]].append({
                    "chunk_id": record["chunk_id"],
                    "difficulty": record["difficulty"],
                    "content_type": record["content_type"],
                    "textbook_id": record["textbook_id"],
                    "position": record["position"]
                })
            
            # Build learning path segments
            segments = []
            covered_concepts = set()
            used_chunks = set()
            
            # Start with prerequisites
            for concept in prerequisites:
                if concept in covered_concepts:
                    continue
                
                chunks = concept_chunks.get(concept, [])
                if not chunks:
                    continue
                
                # Select appropriate chunks based on user level
                selected_chunks = self._select_chunks_for_level(
                    chunks, user_level, used_chunks, limit=5
                )
                
                if selected_chunks:
                    segment = LearningPathSegment(
                        segment_id=f"seg_{len(segments)+1}",
                        concepts=[concept],
                        chunks=[c["chunk_id"] for c in selected_chunks],
                        prerequisites=list(covered_concepts),
                        learning_objectives=[f"Understand {concept}"],
                        estimated_time_minutes=len(selected_chunks) * 5,
                        difficulty_level=np.mean([c["difficulty"] for c in selected_chunks])
                    )
                    segments.append(segment)
                    covered_concepts.add(concept)
                    used_chunks.update(c["chunk_id"] for c in selected_chunks)
            
            # Then target concepts
            for concept in target_concepts:
                if concept in covered_concepts:
                    continue
                
                chunks = concept_chunks.get(concept, [])
                if not chunks:
                    continue
                
                selected_chunks = self._select_chunks_for_level(
                    chunks, user_level, used_chunks, limit=5
                )
                
                if selected_chunks:
                    segment = LearningPathSegment(
                        segment_id=f"seg_{len(segments)+1}",
                        concepts=[concept],
                        chunks=[c["chunk_id"] for c in selected_chunks],
                        prerequisites=list(covered_concepts),
                        learning_objectives=[f"Master {concept}"],
                        estimated_time_minutes=len(selected_chunks) * 5,
                        difficulty_level=np.mean([c["difficulty"] for c in selected_chunks])
                    )
                    segments.append(segment)
                    covered_concepts.add(concept)
                    used_chunks.update(c["chunk_id"] for c in selected_chunks)
            
            # Limit total chunks
            total_chunks = sum(len(seg.chunks) for seg in segments)
            if total_chunks > max_chunks:
                # Trim segments to fit limit
                segments = self._trim_learning_path(segments, max_chunks)
            
            return segments
            
        except Exception as e:
            logger.error(f"Failed to suggest learning path: {e}")
            return []
    
    async def calculate_concept_similarity(
        self,
        concept1: str,
        concept2: str
    ) -> float:
        """
        Calculate similarity between two concepts.
        
        Args:
            concept1: First concept
            concept2: Second concept
            
        Returns:
            Similarity score (0-1)
        """
        try:
            # Check direct relationships
            query = """
                MATCH (c1:Concept {name: $concept1})
                MATCH (c2:Concept {name: $concept2})
                OPTIONAL MATCH path = shortestPath((c1)-[*..5]-(c2))
                RETURN length(path) as distance,
                       [r in relationships(path) | type(r)] as rel_types
            """
            
            results = await self.connection.execute_query(
                query,
                {"concept1": concept1, "concept2": concept2}
            )
            
            if not results or results[0]["distance"] is None:
                # No path found
                return 0.0
            
            distance = results[0]["distance"]
            rel_types = results[0]["rel_types"]
            
            # Calculate similarity based on distance and relationship types
            if distance == 0:
                return 1.0  # Same concept
            
            # Base similarity from distance
            base_similarity = 1.0 / (1 + distance)
            
            # Boost for certain relationship types
            boost = 1.0
            strong_relationships = [
                "REQUIRES", "PREREQUISITE_OF", 
                "BUILDS_UPON", "SIMILAR_TO"
            ]
            
            for rel in rel_types:
                if rel in strong_relationships:
                    boost *= 1.2
            
            # Also check shared chunks
            shared_query = """
                MATCH (c1:Concept {name: $concept1})<-[:MENTIONS_CONCEPT]-(chunk:Chunk)-[:MENTIONS_CONCEPT]->(c2:Concept {name: $concept2})
                RETURN count(distinct chunk) as shared_chunks
            """
            
            shared_results = await self.connection.execute_query(
                shared_query,
                {"concept1": concept1, "concept2": concept2}
            )
            
            shared_chunks = shared_results[0]["shared_chunks"] if shared_results else 0
            
            # Boost for shared content
            if shared_chunks > 0:
                boost *= (1 + min(0.5, shared_chunks * 0.1))
            
            final_similarity = min(1.0, base_similarity * boost)
            
            return final_similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate concept similarity: {e}")
            return 0.0
    
    async def cluster_related_concepts(
        self,
        seed_concepts: List[str],
        similarity_threshold: float = 0.6,
        max_concepts: int = 20
    ) -> List[Set[str]]:
        """
        Cluster related concepts based on similarity.
        
        Args:
            seed_concepts: Starting concepts
            similarity_threshold: Minimum similarity for clustering
            max_concepts: Maximum concepts per cluster
            
        Returns:
            List of concept clusters
        """
        try:
            clusters = []
            processed = set()
            
            for seed in seed_concepts:
                if seed in processed:
                    continue
                
                cluster = {seed}
                processed.add(seed)
                
                # Find related concepts
                query = """
                    MATCH (seed:Concept {name: $seed})
                    MATCH (seed)-[r*1..2]-(related:Concept)
                    WHERE related.name <> $seed
                    AND related.name NOT IN $processed
                    WITH related, count(distinct r) as connection_count
                    ORDER BY connection_count DESC
                    LIMIT $limit
                    RETURN related.name as concept
                """
                
                results = await self.connection.execute_query(
                    query,
                    {
                        "seed": seed,
                        "processed": list(processed),
                        "limit": max_concepts
                    }
                )
                
                # Check similarity with seed
                for record in results:
                    concept = record["concept"]
                    similarity = await self.calculate_concept_similarity(seed, concept)
                    
                    if similarity >= similarity_threshold:
                        cluster.add(concept)
                        processed.add(concept)
                
                if len(cluster) > 1:
                    clusters.append(cluster)
            
            # Merge overlapping clusters
            merged_clusters = self._merge_clusters(clusters)
            
            return merged_clusters
            
        except Exception as e:
            logger.error(f"Failed to cluster concepts: {e}")
            return []
    
    async def get_concept_graph(
        self,
        root_concepts: List[str],
        max_depth: int = 3,
        relationship_types: Optional[List[RelationshipType]] = None
    ) -> ConceptGraph:
        """
        Get a graph of concepts and their relationships.
        
        Args:
            root_concepts: Starting concepts
            max_depth: Maximum depth to traverse
            relationship_types: Types of relationships to include
            
        Returns:
            Concept graph structure
        """
        try:
            if not relationship_types:
                relationship_types = [
                    RelationshipType.REQUIRES,
                    RelationshipType.BUILDS_UPON,
                    RelationshipType.RELATED_TO
                ]
            
            rel_type_str = "|".join(rt.value for rt in relationship_types)
            
            query = """
                UNWIND $roots as root_name
                MATCH (root:Concept {name: root_name})
                CALL apoc.path.subgraphAll(root, {
                    relationshipFilter: $rel_filter,
                    maxLevel: $max_depth
                })
                YIELD nodes, relationships
                RETURN nodes, relationships
            """
            
            results = await self.connection.execute_query(
                query,
                {
                    "roots": root_concepts,
                    "rel_filter": rel_type_str,
                    "max_depth": max_depth
                }
            )
            
            # Aggregate all nodes and relationships
            all_nodes = set()
            all_edges = []
            node_properties = {}
            
            for record in results:
                # Process nodes
                for node in record["nodes"]:
                    node_name = node.get("name")
                    if node_name:
                        all_nodes.add(node_name)
                        node_properties[node_name] = {
                            "type": node.get("type", "unknown"),
                            "difficulty": node.get("difficulty_level", 0.5),
                            "importance": node.get("importance_score", 0.5)
                        }
                
                # Process relationships
                for rel in record["relationships"]:
                    source = rel.start_node.get("name")
                    target = rel.end_node.get("name")
                    rel_type = rel.type
                    
                    if source and target:
                        edge_props = {
                            "type": rel_type,
                            "strength": rel.get("strength", 1.0)
                        }
                        all_edges.append((source, target, edge_props))
            
            return ConceptGraph(
                nodes=all_nodes,
                edges=all_edges,
                node_properties=node_properties
            )
            
        except Exception as e:
            logger.error(f"Failed to get concept graph: {e}")
            return ConceptGraph(set(), [], {})
    
    async def update_similarity_relationships(
        self,
        threshold: float = 0.7,
        batch_size: int = 100
    ) -> int:
        """
        Update similarity relationships between chunks based on embeddings.
        
        Args:
            threshold: Minimum similarity score
            batch_size: Batch size for processing
            
        Returns:
            Number of relationships created/updated
        """
        try:
            # Get total chunk count
            count_query = """
                MATCH (c:Chunk)
                WHERE c.embedding IS NOT NULL
                RETURN count(c) as total
            """
            
            count_result = await self.connection.execute_query(count_query)
            total_chunks = count_result[0]["total"] if count_result else 0
            
            if total_chunks == 0:
                return 0
            
            relationships_created = 0
            
            # Process in batches
            for offset in range(0, total_chunks, batch_size):
                # Use vector index for similarity search
                batch_query = """
                    MATCH (c:Chunk)
                    WHERE c.embedding IS NOT NULL
                    SKIP $offset LIMIT $batch_size
                    CALL db.index.vector.queryNodes('chunkEmbedding', 10, c.embedding)
                    YIELD node, score
                    WHERE node.chunk_id <> c.chunk_id
                    AND score >= $threshold
                    MERGE (c)-[r:SIMILAR_TO]-(node)
                    SET r.similarity = score,
                        r.updated_at = datetime()
                    RETURN count(r) as count
                """
                
                results = await self.connection.execute_query(
                    batch_query,
                    {
                        "offset": offset,
                        "batch_size": batch_size,
                        "threshold": threshold
                    }
                )
                
                if results:
                    relationships_created += sum(r["count"] for r in results)
                
                logger.info(f"Processed {min(offset + batch_size, total_chunks)}/{total_chunks} chunks")
            
            logger.info(f"Created/updated {relationships_created} similarity relationships")
            return relationships_created
            
        except Exception as e:
            logger.error(f"Failed to update similarity relationships: {e}")
            return 0
    
    def _would_create_cycle(
        self,
        source: str,
        target: str,
        relationship_type: RelationshipType
    ) -> bool:
        """Check if creating a relationship would create a cycle"""
        # For prerequisite relationships, check if target can reach source
        if relationship_type == RelationshipType.REQUIRES:
            # source requires target, so check if target requires source (directly or indirectly)
            query = """
                MATCH path = (target:Concept {name: $target})-[:REQUIRES*]->(source:Concept {name: $source})
                RETURN count(path) > 0 as has_cycle
            """
        else:
            # For other relationships, use general path checking
            query = """
                MATCH path = (target:Concept {name: $target})-[*]->(source:Concept {name: $source})
                RETURN count(path) > 0 as has_cycle
            """
        
        # This would need to be made async in practice
        # For now, return False to avoid blocking
        return False
    
    def _calculate_levels(
        self,
        nodes: List[str],
        tree: Dict[str, List[str]],
        levels: Dict[str, int],
        current_level: int
    ) -> None:
        """Recursively calculate concept levels"""
        for node in nodes:
            if node not in levels or levels[node] > current_level:
                levels[node] = current_level
                
                if node in tree:
                    self._calculate_levels(
                        tree[node],
                        tree,
                        levels,
                        current_level + 1
                    )
    
    def _select_chunks_for_level(
        self,
        chunks: List[Dict[str, Any]],
        user_level: str,
        used_chunks: Set[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Select appropriate chunks based on user level"""
        # Filter out used chunks
        available = [c for c in chunks if c["chunk_id"] not in used_chunks]
        
        if not available:
            return []
        
        # Define difficulty ranges for levels
        level_ranges = {
            "beginner": (0.0, 0.4),
            "intermediate": (0.3, 0.7),
            "advanced": (0.6, 1.0)
        }
        
        min_diff, max_diff = level_ranges.get(user_level, (0.0, 1.0))
        
        # Filter by difficulty
        suitable = [
            c for c in available
            if min_diff <= c["difficulty"] <= max_diff
        ]
        
        # If not enough suitable chunks, include some outside range
        if len(suitable) < limit:
            suitable.extend([
                c for c in available
                if c not in suitable
            ])
        
        # Prioritize by content type and position
        content_priority = {
            "definition": 1,
            "explanation": 2,
            "example": 3,
            "theory": 4,
            "exercise": 5
        }
        
        suitable.sort(
            key=lambda c: (
                content_priority.get(c["content_type"], 6),
                abs(c["difficulty"] - (min_diff + max_diff) / 2),
                c["position"]
            )
        )
        
        return suitable[:limit]
    
    def _trim_learning_path(
        self,
        segments: List[LearningPathSegment],
        max_chunks: int
    ) -> List[LearningPathSegment]:
        """Trim learning path to fit chunk limit"""
        total_chunks = 0
        trimmed_segments = []
        
        for segment in segments:
            if total_chunks + len(segment.chunks) <= max_chunks:
                trimmed_segments.append(segment)
                total_chunks += len(segment.chunks)
            else:
                # Partially include this segment
                remaining = max_chunks - total_chunks
                if remaining > 0:
                    trimmed_segment = LearningPathSegment(
                        segment_id=segment.segment_id,
                        concepts=segment.concepts,
                        chunks=segment.chunks[:remaining],
                        prerequisites=segment.prerequisites,
                        learning_objectives=segment.learning_objectives,
                        estimated_time_minutes=remaining * 5,
                        difficulty_level=segment.difficulty_level
                    )
                    trimmed_segments.append(trimmed_segment)
                break
        
        return trimmed_segments
    
    def _merge_clusters(
        self,
        clusters: List[Set[str]]
    ) -> List[Set[str]]:
        """Merge overlapping clusters"""
        if not clusters:
            return []
        
        merged = []
        used = set()
        
        for i, cluster1 in enumerate(clusters):
            if i in used:
                continue
            
            merged_cluster = set(cluster1)
            used.add(i)
            
            for j, cluster2 in enumerate(clusters[i+1:], i+1):
                if j in used:
                    continue
                
                if merged_cluster & cluster2:  # Overlap exists
                    merged_cluster.update(cluster2)
                    used.add(j)
            
            merged.append(merged_cluster)
        
        return merged