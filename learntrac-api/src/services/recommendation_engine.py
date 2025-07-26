"""Recommendation Engine Service

An intelligent recommendation system that suggests educational content
based on multiple factors:
- User learning progress and patterns
- Content difficulty progression
- Prerequisite satisfaction
- Learning objectives alignment
- Collaborative filtering
- Content-based filtering
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import asyncio
import json

from ..db.database import DatabaseManager
from ..services.redis_client import RedisCache
from ..pdf_processing.neo4j_search import Neo4jVectorSearch
from ..services.learning_progress_tracker import LearningProgressTracker
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ContentRecommendation:
    """Represents a content recommendation"""
    chunk_id: str
    score: float
    reason: str
    concept_id: str
    concept_name: str
    difficulty: float
    estimated_time_minutes: int
    prerequisites_met: bool
    relevance_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class LearningPathRecommendation:
    """Represents a learning path recommendation"""
    path_id: str
    target_concepts: List[str]
    recommended_chunks: List[str]
    total_time_hours: float
    difficulty_progression: List[float]
    prerequisite_order: List[str]
    confidence_score: float
    

@dataclass
class UserProfile:
    """User learning profile for recommendations"""
    user_id: str
    learning_style: str  # visual, reading, practice, mixed
    pace: str  # fast, moderate, slow
    interests: List[str]
    strengths: List[str]
    weaknesses: List[str]
    preferred_difficulty: float
    available_time_daily: int  # minutes
    goals: List[str]
    

class RecommendationEngine:
    """
    Advanced recommendation engine for educational content.
    
    Uses hybrid approach combining:
    - Collaborative filtering (user-user, item-item)
    - Content-based filtering (embeddings, topics)
    - Knowledge graph traversal (prerequisites)
    - Learning science principles (spacing, interleaving)
    - Contextual factors (time, progress, goals)
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_cache: RedisCache,
        neo4j_search: Neo4jVectorSearch,
        progress_tracker: LearningProgressTracker,
        embedding_service: EmbeddingService
    ):
        self.db_manager = db_manager
        self.redis_cache = redis_cache
        self.neo4j_search = neo4j_search
        self.progress_tracker = progress_tracker
        self.embedding_service = embedding_service
        
        # Configuration
        self.cache_ttl = 3600  # 1 hour
        self.min_similarity_threshold = 0.6
        self.exploration_rate = 0.2  # 20% exploration vs exploitation
        self.difficulty_tolerance = 0.3  # +/- 30% difficulty range
        
        # Weights for hybrid scoring
        self.weights = {
            "content_similarity": 0.25,
            "collaborative": 0.20,
            "prerequisite": 0.20,
            "difficulty": 0.15,
            "recency": 0.10,
            "diversity": 0.10
        }
        
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the recommendation engine"""
        try:
            await self._create_tables()
            await self._precompute_similarities()
            self._initialized = True
            logger.info("RecommendationEngine initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize RecommendationEngine: {e}")
            return False
    
    # ===== Main Recommendation Methods =====
    
    async def get_recommendations(
        self,
        user_id: str,
        limit: int = 10,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ContentRecommendation]:
        """
        Get personalized content recommendations.
        
        Args:
            user_id: User ID
            limit: Number of recommendations
            context: Optional context (current topic, time available, etc)
            
        Returns:
            List of content recommendations
        """
        # Check cache first
        cache_key = f"recommendations:{user_id}:{limit}"
        cached = await self.redis_cache.get(cache_key)
        if cached:
            return self._deserialize_recommendations(cached)
        
        # Get user profile and progress
        user_profile = await self._get_user_profile(user_id)
        user_progress = await self.progress_tracker.get_learning_analytics(user_id)
        
        # Get candidate content
        candidates = await self._get_candidate_content(
            user_id, user_profile, limit * 5  # Get more candidates for filtering
        )
        
        # Score candidates using hybrid approach
        scored_candidates = []
        for candidate in candidates:
            scores = await self._score_candidate(
                candidate, user_id, user_profile, user_progress, context
            )
            
            total_score = sum(
                self.weights[factor] * score 
                for factor, score in scores.items()
            )
            
            # Create recommendation
            recommendation = await self._create_recommendation(
                candidate, total_score, scores
            )
            scored_candidates.append(recommendation)
        
        # Sort and filter
        recommendations = sorted(
            scored_candidates, 
            key=lambda r: r.score, 
            reverse=True
        )[:limit]
        
        # Apply diversity boost
        recommendations = self._apply_diversity_boost(recommendations)
        
        # Cache results
        await self.redis_cache.set(
            cache_key,
            self._serialize_recommendations(recommendations),
            ttl=self.cache_ttl
        )
        
        return recommendations
    
    async def get_learning_path_recommendation(
        self,
        user_id: str,
        target_concepts: List[str],
        time_constraint_hours: Optional[int] = None
    ) -> LearningPathRecommendation:
        """
        Recommend an optimal learning path.
        
        Args:
            user_id: User ID
            target_concepts: Target concepts to master
            time_constraint_hours: Optional time constraint
            
        Returns:
            Learning path recommendation
        """
        # Get user profile and current knowledge
        user_profile = await self._get_user_profile(user_id)
        current_knowledge = await self._get_user_knowledge_state(user_id)
        
        # Build prerequisite graph
        prereq_graph = await self._build_prerequisite_graph(target_concepts)
        
        # Find optimal path using topological sort with constraints
        path_concepts = await self._find_optimal_path(
            current_knowledge,
            target_concepts,
            prereq_graph,
            user_profile
        )
        
        # Select best chunks for each concept
        path_chunks = []
        total_time = 0
        difficulties = []
        
        for concept_id in path_concepts:
            chunk = await self._select_best_chunk_for_concept(
                user_id, concept_id, user_profile
            )
            if chunk:
                path_chunks.append(chunk["chunk_id"])
                total_time += chunk["estimated_time"]
                difficulties.append(chunk["difficulty"])
        
        # Apply time constraint if needed
        if time_constraint_hours and total_time > time_constraint_hours * 60:
            path_chunks, total_time = await self._optimize_for_time_constraint(
                path_chunks, time_constraint_hours * 60
            )
        
        # Calculate confidence score
        confidence = self._calculate_path_confidence(
            path_concepts, prereq_graph, current_knowledge
        )
        
        return LearningPathRecommendation(
            path_id=f"path_{user_id}_{int(datetime.utcnow().timestamp())}",
            target_concepts=target_concepts,
            recommended_chunks=path_chunks,
            total_time_hours=total_time / 60,
            difficulty_progression=difficulties,
            prerequisite_order=path_concepts,
            confidence_score=confidence
        )
    
    async def get_similar_content(
        self,
        chunk_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get content similar to a given chunk.
        
        Args:
            chunk_id: Reference chunk ID
            limit: Number of similar items
            
        Returns:
            List of similar content
        """
        # Get chunk embedding
        chunk_data = await self._get_chunk_data(chunk_id)
        if not chunk_data:
            return []
        
        # Search by embedding similarity
        similar = await self.neo4j_search.search_similar_chunks(
            embedding=chunk_data["embedding"],
            limit=limit + 1,  # +1 to exclude self
            filters={"exclude_chunks": [chunk_id]}
        )
        
        return [
            {
                "chunk_id": s.chunk_id,
                "similarity_score": s.score,
                "title": s.section_title,
                "concepts": s.concepts[:5]
            }
            for s in similar.results
        ][:limit]
    
    async def get_remedial_content(
        self,
        user_id: str,
        concept_id: str
    ) -> List[ContentRecommendation]:
        """
        Get remedial content for struggling concepts.
        
        Args:
            user_id: User ID
            concept_id: Concept needing remediation
            
        Returns:
            List of remedial content recommendations
        """
        # Get concept prerequisites
        prerequisites = await self._get_concept_prerequisites(concept_id)
        
        # Check which prerequisites need reinforcement
        weak_prerequisites = []
        for prereq in prerequisites:
            mastery = await self.progress_tracker.calculate_concept_mastery(
                user_id, prereq["concept_id"]
            )
            if mastery.mastery_level < 0.7:
                weak_prerequisites.append(prereq)
        
        # Get remedial content for weak prerequisites
        recommendations = []
        for prereq in weak_prerequisites:
            chunks = await self._get_concept_chunks(
                prereq["concept_id"],
                difficulty_range=(0, 0.5)  # Easier content
            )
            
            for chunk in chunks[:2]:  # Max 2 per prerequisite
                rec = ContentRecommendation(
                    chunk_id=chunk["chunk_id"],
                    score=0.9,  # High priority
                    reason=f"Strengthen prerequisite: {prereq['concept_name']}",
                    concept_id=prereq["concept_id"],
                    concept_name=prereq["concept_name"],
                    difficulty=chunk["difficulty"],
                    estimated_time_minutes=chunk["estimated_time"],
                    prerequisites_met=True
                )
                recommendations.append(rec)
        
        # Add alternative explanations for the main concept
        alt_chunks = await self._get_alternative_explanations(
            concept_id, user_id
        )
        
        for chunk in alt_chunks:
            rec = ContentRecommendation(
                chunk_id=chunk["chunk_id"],
                score=0.85,
                reason="Alternative explanation",
                concept_id=concept_id,
                concept_name=chunk["concept_name"],
                difficulty=chunk["difficulty"],
                estimated_time_minutes=chunk["estimated_time"],
                prerequisites_met=True
            )
            recommendations.append(rec)
        
        return sorted(recommendations, key=lambda r: r.score, reverse=True)
    
    # ===== Scoring Methods =====
    
    async def _score_candidate(
        self,
        candidate: Dict[str, Any],
        user_id: str,
        user_profile: UserProfile,
        user_progress: Any,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Score a candidate using multiple factors.
        
        Returns:
            Dictionary of factor scores
        """
        scores = {}
        
        # Content similarity score
        scores["content_similarity"] = await self._calculate_content_similarity(
            candidate, user_id, context
        )
        
        # Collaborative filtering score  
        scores["collaborative"] = await self._calculate_collaborative_score(
            candidate["chunk_id"], user_id
        )
        
        # Prerequisite satisfaction score
        scores["prerequisite"] = await self._calculate_prerequisite_score(
            candidate["concept_id"], user_id
        )
        
        # Difficulty appropriateness score
        scores["difficulty"] = self._calculate_difficulty_score(
            candidate["difficulty"], user_profile, user_progress
        )
        
        # Recency/spacing score
        scores["recency"] = await self._calculate_recency_score(
            candidate["chunk_id"], user_id
        )
        
        # Diversity score
        scores["diversity"] = await self._calculate_diversity_score(
            candidate["concept_id"], user_id
        )
        
        return scores
    
    async def _calculate_content_similarity(
        self,
        candidate: Dict[str, Any],
        user_id: str,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate content-based similarity score"""
        # Get user interest embedding
        user_interests = await self._get_user_interest_embedding(user_id)
        
        if user_interests is None:
            return 0.5  # Neutral score
        
        # Get candidate embedding
        candidate_embedding = candidate.get("embedding")
        if not candidate_embedding:
            chunk_data = await self._get_chunk_data(candidate["chunk_id"])
            candidate_embedding = chunk_data.get("embedding", [])
        
        if not candidate_embedding:
            return 0.5
        
        # Calculate cosine similarity
        similarity = cosine_similarity(
            [user_interests],
            [candidate_embedding]
        )[0][0]
        
        # Boost if matches current context
        if context and context.get("current_topic"):
            topic_match = any(
                concept == context["current_topic"] 
                for concept in candidate.get("concepts", [])
            )
            if topic_match:
                similarity = min(1.0, similarity + 0.2)
        
        return max(0, min(1, similarity))
    
    async def _calculate_collaborative_score(
        self,
        chunk_id: str,
        user_id: str
    ) -> float:
        """Calculate collaborative filtering score"""
        # Get similar users
        similar_users = await self._get_similar_users(user_id, limit=10)
        
        if not similar_users:
            return 0.5
        
        # Check how many similar users found this helpful
        positive_ratings = 0
        total_ratings = 0
        
        for similar_user in similar_users:
            rating = await self._get_user_chunk_rating(
                similar_user["user_id"], chunk_id
            )
            if rating is not None:
                total_ratings += 1
                if rating > 0.7:  # Positive threshold
                    positive_ratings += 1
        
        if total_ratings == 0:
            return 0.5  # No data
        
        # Weight by user similarity
        weighted_score = positive_ratings / total_ratings
        avg_similarity = np.mean([u["similarity"] for u in similar_users])
        
        return weighted_score * avg_similarity
    
    async def _calculate_prerequisite_score(
        self,
        concept_id: str,
        user_id: str
    ) -> float:
        """Calculate prerequisite satisfaction score"""
        prerequisites = await self._get_concept_prerequisites(concept_id)
        
        if not prerequisites:
            return 1.0  # No prerequisites
        
        satisfied_count = 0
        total_weight = 0
        
        for prereq in prerequisites:
            mastery = await self.progress_tracker.calculate_concept_mastery(
                user_id, prereq["concept_id"]
            )
            
            weight = prereq.get("importance", 1.0)
            total_weight += weight
            
            if mastery.mastery_level >= 0.7:
                satisfied_count += weight
        
        return satisfied_count / total_weight if total_weight > 0 else 0
    
    def _calculate_difficulty_score(
        self,
        difficulty: float,
        user_profile: UserProfile,
        user_progress: Any
    ) -> float:
        """Calculate difficulty appropriateness score"""
        # Get user's optimal difficulty
        current_level = user_progress.average_understanding
        optimal_difficulty = min(0.9, current_level + 0.1)  # Slightly above current
        
        # Account for user preference
        if user_profile.pace == "fast":
            optimal_difficulty += 0.1
        elif user_profile.pace == "slow":
            optimal_difficulty -= 0.1
        
        optimal_difficulty = max(0.1, min(0.9, optimal_difficulty))
        
        # Calculate score based on distance from optimal
        distance = abs(difficulty - optimal_difficulty)
        score = 1.0 - (distance / self.difficulty_tolerance)
        
        return max(0, min(1, score))
    
    async def _calculate_recency_score(
        self,
        chunk_id: str,
        user_id: str
    ) -> float:
        """Calculate recency/spacing score"""
        # Get last study time
        last_study = await self.db_manager.fetch_one(
            """
            SELECT last_reviewed
            FROM user_chunk_progress
            WHERE user_id = $1 AND chunk_id = $2
            """,
            user_id, chunk_id
        )
        
        if not last_study or not last_study["last_reviewed"]:
            return 1.0  # Never studied
        
        # Calculate days since last review
        days_since = (datetime.utcnow() - last_study["last_reviewed"]).days
        
        # Optimal spacing curve (simplified Ebbinghaus)
        if days_since < 1:
            return 0.2  # Too recent
        elif days_since < 3:
            return 0.5
        elif days_since < 7:
            return 0.8
        elif days_since < 14:
            return 0.9
        else:
            return 1.0  # Need review
    
    async def _calculate_diversity_score(
        self,
        concept_id: str,
        user_id: str
    ) -> float:
        """Calculate topic diversity score"""
        # Get recently studied concepts
        recent_concepts = await self.db_manager.fetch_all(
            """
            SELECT DISTINCT concept_id
            FROM user_concept_progress
            WHERE user_id = $1 
                AND last_reviewed > $2
            ORDER BY last_reviewed DESC
            LIMIT 10
            """,
            user_id, datetime.utcnow() - timedelta(days=1)
        )
        
        recent_ids = [c["concept_id"] for c in recent_concepts]
        
        if concept_id in recent_ids:
            # Penalty for repetition
            position = recent_ids.index(concept_id)
            return 0.5 - (0.05 * (10 - position))  # More recent = lower score
        
        # Bonus for new topic
        return 1.0
    
    # ===== Helper Methods =====
    
    async def _get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile"""
        profile_data = await self.db_manager.fetch_one(
            """
            SELECT * FROM user_learning_profiles
            WHERE user_id = $1
            """,
            user_id
        )
        
        if profile_data:
            return UserProfile(
                user_id=user_id,
                learning_style=profile_data["learning_style"],
                pace=profile_data["pace"],
                interests=profile_data["interests"],
                strengths=profile_data["strengths"],
                weaknesses=profile_data["weaknesses"],
                preferred_difficulty=profile_data["preferred_difficulty"],
                available_time_daily=profile_data["available_time_daily"],
                goals=profile_data["goals"]
            )
        
        # Create default profile
        default_profile = UserProfile(
            user_id=user_id,
            learning_style="mixed",
            pace="moderate",
            interests=[],
            strengths=[],
            weaknesses=[],
            preferred_difficulty=0.5,
            available_time_daily=30,
            goals=[]
        )
        
        # Save profile
        await self._save_user_profile(default_profile)
        
        return default_profile
    
    async def _save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile"""
        await self.db_manager.execute(
            """
            INSERT INTO user_learning_profiles
            (user_id, learning_style, pace, interests, strengths,
             weaknesses, preferred_difficulty, available_time_daily, goals)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (user_id)
            DO UPDATE SET
                learning_style = EXCLUDED.learning_style,
                pace = EXCLUDED.pace,
                interests = EXCLUDED.interests,
                strengths = EXCLUDED.strengths,
                weaknesses = EXCLUDED.weaknesses,
                preferred_difficulty = EXCLUDED.preferred_difficulty,
                available_time_daily = EXCLUDED.available_time_daily,
                goals = EXCLUDED.goals
            """,
            profile.user_id, profile.learning_style, profile.pace,
            profile.interests, profile.strengths, profile.weaknesses,
            profile.preferred_difficulty, profile.available_time_daily,
            profile.goals
        )
    
    async def _get_candidate_content(
        self,
        user_id: str,
        user_profile: UserProfile,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get candidate content for recommendations"""
        # Mix of different content sources
        candidates = []
        
        # 1. Content based on interests
        if user_profile.interests:
            interest_content = await self._get_content_by_interests(
                user_profile.interests, limit // 3
            )
            candidates.extend(interest_content)
        
        # 2. Next concepts in learning path
        path_content = await self._get_learning_path_content(
            user_id, limit // 3
        )
        candidates.extend(path_content)
        
        # 3. Popular content among similar users
        popular_content = await self._get_popular_content(
            user_id, limit // 3
        )
        candidates.extend(popular_content)
        
        # 4. Exploration content (random high-quality)
        if np.random.random() < self.exploration_rate:
            exploration_content = await self._get_exploration_content(
                limit // 4
            )
            candidates.extend(exploration_content)
        
        # Remove duplicates
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c["chunk_id"] not in seen:
                seen.add(c["chunk_id"])
                unique_candidates.append(c)
        
        return unique_candidates[:limit]
    
    async def _create_recommendation(
        self,
        candidate: Dict[str, Any],
        score: float,
        score_breakdown: Dict[str, float]
    ) -> ContentRecommendation:
        """Create recommendation object"""
        # Generate explanation
        reason = self._generate_recommendation_reason(score_breakdown)
        
        # Check prerequisites
        prereqs_met = score_breakdown.get("prerequisite", 0) > 0.7
        
        return ContentRecommendation(
            chunk_id=candidate["chunk_id"],
            score=score,
            reason=reason,
            concept_id=candidate["concept_id"],
            concept_name=candidate["concept_name"],
            difficulty=candidate["difficulty"],
            estimated_time_minutes=candidate["estimated_time"],
            prerequisites_met=prereqs_met,
            relevance_scores=score_breakdown,
            metadata={
                "textbook": candidate.get("textbook_title"),
                "chapter": candidate.get("chapter_title")
            }
        )
    
    def _generate_recommendation_reason(self, scores: Dict[str, float]) -> str:
        """Generate human-readable recommendation reason"""
        # Find the highest contributing factor
        top_factor = max(scores.items(), key=lambda x: x[1] * self.weights.get(x[0], 0))
        
        reasons = {
            "content_similarity": "Matches your interests and recent topics",
            "collaborative": "Other similar learners found this helpful",
            "prerequisite": "You're ready for this concept",
            "difficulty": "Perfect difficulty level for your progress",
            "recency": "Good time to review this material",
            "diversity": "Explores new related concepts"
        }
        
        return reasons.get(top_factor[0], "Recommended based on your learning profile")
    
    def _apply_diversity_boost(self, recommendations: List[ContentRecommendation]) -> List[ContentRecommendation]:
        """Apply diversity boost to avoid too similar recommendations"""
        if len(recommendations) <= 1:
            return recommendations
        
        diverse_recs = [recommendations[0]]  # Keep top recommendation
        
        for rec in recommendations[1:]:
            # Check similarity to already selected
            is_diverse = True
            for selected in diverse_recs:
                if rec.concept_id == selected.concept_id:
                    # Same concept - apply penalty
                    rec.score *= 0.7
                    is_diverse = False
                    break
            
            if is_diverse or rec.score > 0.8:  # Keep if still high score
                diverse_recs.append(rec)
        
        return diverse_recs
    
    async def _create_tables(self) -> None:
        """Create necessary tables for recommendations"""
        await self.db_manager.execute_many([
            """
            CREATE TABLE IF NOT EXISTS user_learning_profiles (
                user_id VARCHAR(255) PRIMARY KEY,
                learning_style VARCHAR(50) DEFAULT 'mixed',
                pace VARCHAR(50) DEFAULT 'moderate',
                interests TEXT[] DEFAULT '{}',
                strengths TEXT[] DEFAULT '{}', 
                weaknesses TEXT[] DEFAULT '{}',
                preferred_difficulty FLOAT DEFAULT 0.5,
                available_time_daily INTEGER DEFAULT 30,
                goals TEXT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_content_ratings (
                user_id VARCHAR(255) NOT NULL,
                chunk_id VARCHAR(255) NOT NULL,
                rating FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, chunk_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS content_similarity_cache (
                chunk_id_1 VARCHAR(255) NOT NULL,
                chunk_id_2 VARCHAR(255) NOT NULL,
                similarity_score FLOAT NOT NULL,
                computed_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (chunk_id_1, chunk_id_2)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_similarity_cache (
                user_id_1 VARCHAR(255) NOT NULL,
                user_id_2 VARCHAR(255) NOT NULL,
                similarity_score FLOAT NOT NULL,
                computed_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id_1, user_id_2),
                FOREIGN KEY (user_id_1) REFERENCES users(id),
                FOREIGN KEY (user_id_2) REFERENCES users(id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_content_ratings_user 
                ON user_content_ratings(user_id);
            CREATE INDEX IF NOT EXISTS idx_content_ratings_chunk 
                ON user_content_ratings(chunk_id);
            CREATE INDEX IF NOT EXISTS idx_content_similarity_chunk 
                ON content_similarity_cache(chunk_id_1);
            CREATE INDEX IF NOT EXISTS idx_user_similarity_user 
                ON user_similarity_cache(user_id_1);
            """
        ])
    
    async def _precompute_similarities(self) -> None:
        """Precompute content similarities for efficiency"""
        # This would be done periodically in production
        # For now, we compute on-demand and cache
        logger.info("Similarity precomputation scheduled")
    
    def _serialize_recommendations(self, recommendations: List[ContentRecommendation]) -> str:
        """Serialize recommendations for caching"""
        return json.dumps([
            {
                "chunk_id": r.chunk_id,
                "score": r.score,
                "reason": r.reason,
                "concept_id": r.concept_id,
                "concept_name": r.concept_name,
                "difficulty": r.difficulty,
                "estimated_time_minutes": r.estimated_time_minutes,
                "prerequisites_met": r.prerequisites_met,
                "relevance_scores": r.relevance_scores,
                "metadata": r.metadata
            }
            for r in recommendations
        ])
    
    def _deserialize_recommendations(self, data: str) -> List[ContentRecommendation]:
        """Deserialize recommendations from cache"""
        items = json.loads(data)
        return [
            ContentRecommendation(**item)
            for item in items
        ]
    
    # Additional helper methods would be implemented here...