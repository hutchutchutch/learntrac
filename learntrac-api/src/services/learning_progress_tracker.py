"""Learning Progress Tracker Service

A comprehensive service for tracking and analyzing user learning progress.
Features:
- Real-time progress tracking
- Spaced repetition scheduling
- Mastery level calculations
- Performance analytics
- Learning path optimization
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict
import asyncio
import json

from ..db.database import DatabaseManager
from ..services.redis_client import RedisCache
from ..pdf_processing.neo4j_search import Neo4jVectorSearch

logger = logging.getLogger(__name__)


@dataclass
class LearningSession:
    """Represents a single learning session"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    chunks_studied: List[str] = field(default_factory=list)
    total_time_seconds: int = 0
    understanding_scores: Dict[str, float] = field(default_factory=dict)
    concepts_covered: List[str] = field(default_factory=list)
    

@dataclass
class ConceptMastery:
    """Tracks mastery of a specific concept"""
    concept_id: str
    concept_name: str
    first_seen: datetime
    last_reviewed: datetime
    total_reviews: int
    average_understanding: float
    mastery_level: float
    retention_strength: float
    next_review_date: datetime
    related_chunks: List[str]
    

@dataclass 
class LearningAnalytics:
    """Learning analytics for a user"""
    total_study_time_hours: float
    total_concepts_studied: int
    concepts_mastered: int
    average_understanding: float
    learning_velocity: float  # Concepts per hour
    retention_rate: float
    strengths: List[str]
    weaknesses: List[str]
    recommended_review: List[str]
    

@dataclass
class SpacedRepetitionSchedule:
    """Spaced repetition schedule for a concept"""
    concept_id: str
    interval_days: int
    ease_factor: float
    next_review: datetime
    repetition_number: int
    

class LearningProgressTracker:
    """
    Comprehensive learning progress tracking service.
    
    Features:
    - Real-time progress tracking
    - Spaced repetition algorithm (SM-2)
    - Concept mastery calculations
    - Learning analytics
    - Performance predictions
    - Adaptive learning recommendations
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_cache: RedisCache,
        neo4j_search: Neo4jVectorSearch
    ):
        self.db_manager = db_manager
        self.redis_cache = redis_cache
        self.neo4j_search = neo4j_search
        
        # Configuration
        self.mastery_threshold = 0.8
        self.retention_decay_rate = 0.1  # Per day
        self.initial_ease_factor = 2.5
        self.minimum_ease_factor = 1.3
        
        # Initialize tables
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the learning progress tracker"""
        try:
            await self._create_tables()
            self._initialized = True
            logger.info("LearningProgressTracker initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LearningProgressTracker: {e}")
            return False
    
    # ===== Session Management =====
    
    async def start_session(
        self,
        user_id: str,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new learning session.
        
        Args:
            user_id: User ID
            session_metadata: Optional metadata for the session
            
        Returns:
            Session ID
        """
        session_id = f"session_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        session = LearningSession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.utcnow()
        )
        
        # Store in Redis for real-time tracking
        await self.redis_cache.set(
            f"learning_session:{session_id}",
            {
                "user_id": user_id,
                "start_time": session.start_time.isoformat(),
                "metadata": session_metadata or {}
            },
            ttl=86400  # 24 hours
        )
        
        # Store in database
        await self.db_manager.execute(
            """
            INSERT INTO learning_sessions 
            (session_id, user_id, start_time, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            session_id, user_id, session.start_time, 
            json.dumps(session_metadata) if session_metadata else "{}"
        )
        
        return session_id
    
    async def end_session(self, session_id: str) -> LearningSession:
        """
        End a learning session and calculate statistics.
        
        Args:
            session_id: Session ID
            
        Returns:
            Completed session data
        """
        # Get session from Redis
        session_data = await self.redis_cache.get(f"learning_session:{session_id}")
        if not session_data:
            raise ValueError(f"Session {session_id} not found")
        
        end_time = datetime.utcnow()
        start_time = datetime.fromisoformat(session_data["start_time"])
        total_time = int((end_time - start_time).total_seconds())
        
        # Get session progress from database
        progress_data = await self.db_manager.fetch_all(
            """
            SELECT chunk_id, understanding_level, time_spent_seconds
            FROM session_progress
            WHERE session_id = $1
            """,
            session_id
        )
        
        chunks_studied = [p["chunk_id"] for p in progress_data]
        understanding_scores = {
            p["chunk_id"]: p["understanding_level"] 
            for p in progress_data
        }
        
        # Get concepts covered
        concepts = set()
        for chunk_id in chunks_studied:
            chunk_concepts = await self._get_chunk_concepts(chunk_id)
            concepts.update(chunk_concepts)
        
        # Update session in database
        await self.db_manager.execute(
            """
            UPDATE learning_sessions
            SET end_time = $1, total_time_seconds = $2,
                chunks_studied = $3, average_understanding = $4
            WHERE session_id = $5
            """,
            end_time, total_time, len(chunks_studied),
            np.mean(list(understanding_scores.values())) if understanding_scores else 0,
            session_id
        )
        
        # Clean up Redis
        await self.redis_cache.delete(f"learning_session:{session_id}")
        
        return LearningSession(
            session_id=session_id,
            user_id=session_data["user_id"],
            start_time=start_time,
            end_time=end_time,
            chunks_studied=chunks_studied,
            total_time_seconds=total_time,
            understanding_scores=understanding_scores,
            concepts_covered=list(concepts)
        )
    
    async def track_chunk_progress(
        self,
        session_id: str,
        chunk_id: str,
        time_spent_seconds: int,
        understanding_level: float,
        interaction_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track progress on a specific chunk.
        
        Args:
            session_id: Active session ID
            chunk_id: Chunk being studied
            time_spent_seconds: Time spent on chunk
            understanding_level: Self-reported understanding (0-1)
            interaction_data: Optional interaction metrics
            
        Returns:
            Success status
        """
        try:
            # Validate session exists
            session_data = await self.redis_cache.get(f"learning_session:{session_id}")
            if not session_data:
                raise ValueError(f"Session {session_id} not found or expired")
            
            user_id = session_data["user_id"]
            
            # Store progress
            await self.db_manager.execute(
                """
                INSERT INTO session_progress
                (session_id, chunk_id, time_spent_seconds, understanding_level,
                 interaction_data, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                session_id, chunk_id, time_spent_seconds, understanding_level,
                json.dumps(interaction_data) if interaction_data else "{}",
                datetime.utcnow()
            )
            
            # Update user progress
            await self.db_manager.execute(
                """
                INSERT INTO user_chunk_progress
                (user_id, chunk_id, total_time_seconds, 
                 last_understanding_level, review_count, last_reviewed)
                VALUES ($1, $2, $3, $4, 1, $5)
                ON CONFLICT (user_id, chunk_id)
                DO UPDATE SET
                    total_time_seconds = user_chunk_progress.total_time_seconds + $3,
                    last_understanding_level = $4,
                    review_count = user_chunk_progress.review_count + 1,
                    last_reviewed = $5
                """,
                user_id, chunk_id, time_spent_seconds, 
                understanding_level, datetime.utcnow()
            )
            
            # Update concept progress
            concepts = await self._get_chunk_concepts(chunk_id)
            for concept in concepts:
                await self._update_concept_progress(
                    user_id, concept, understanding_level
                )
            
            # Cache for real-time analytics
            await self.redis_cache.hincrby(
                f"user_stats:{user_id}:daily:{datetime.utcnow().date()}",
                "chunks_studied", 1
            )
            await self.redis_cache.hincrby(
                f"user_stats:{user_id}:daily:{datetime.utcnow().date()}",
                "time_spent", time_spent_seconds
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to track chunk progress: {e}")
            return False
    
    # ===== Mastery Calculation =====
    
    async def calculate_concept_mastery(
        self,
        user_id: str,
        concept_id: str
    ) -> ConceptMastery:
        """
        Calculate mastery level for a concept.
        
        Uses multiple factors:
        - Understanding scores
        - Review frequency
        - Time decay
        - Related chunk performance
        
        Args:
            user_id: User ID
            concept_id: Concept ID
            
        Returns:
            Concept mastery data
        """
        # Get concept data
        concept_data = await self.db_manager.fetch_one(
            """
            SELECT c.*, ucp.first_seen, ucp.last_reviewed, 
                   ucp.total_reviews, ucp.average_understanding,
                   ucp.spaced_repetition_data
            FROM concepts c
            LEFT JOIN user_concept_progress ucp 
                ON c.concept_id = ucp.concept_id AND ucp.user_id = $1
            WHERE c.concept_id = $2
            """,
            user_id, concept_id
        )
        
        if not concept_data:
            raise ValueError(f"Concept {concept_id} not found")
        
        # Get related chunks and their progress
        chunk_progress = await self.db_manager.fetch_all(
            """
            SELECT cc.chunk_id, ucp.last_understanding_level,
                   ucp.total_time_seconds, ucp.review_count,
                   ucp.last_reviewed
            FROM concept_chunks cc
            LEFT JOIN user_chunk_progress ucp
                ON cc.chunk_id = ucp.chunk_id AND ucp.user_id = $1
            WHERE cc.concept_id = $2
            """,
            user_id, concept_id
        )
        
        # Calculate mastery components
        if not chunk_progress or not any(p["last_understanding_level"] for p in chunk_progress):
            # No progress yet
            mastery_level = 0.0
            retention_strength = 0.0
            average_understanding = 0.0
        else:
            # Understanding component
            understanding_scores = [
                p["last_understanding_level"] 
                for p in chunk_progress 
                if p["last_understanding_level"] is not None
            ]
            average_understanding = np.mean(understanding_scores) if understanding_scores else 0
            
            # Frequency component
            total_reviews = sum(p["review_count"] or 0 for p in chunk_progress)
            frequency_factor = min(1.0, total_reviews / 5)  # Cap at 5 reviews
            
            # Time decay component
            if concept_data["last_reviewed"]:
                days_since_review = (datetime.utcnow() - concept_data["last_reviewed"]).days
                retention_strength = np.exp(-self.retention_decay_rate * days_since_review)
            else:
                retention_strength = 0.0
            
            # Combined mastery score
            mastery_level = (
                0.5 * average_understanding +
                0.3 * frequency_factor + 
                0.2 * retention_strength
            )
        
        # Calculate next review date using spaced repetition
        next_review = await self._calculate_next_review(
            user_id, concept_id, average_understanding
        )
        
        return ConceptMastery(
            concept_id=concept_id,
            concept_name=concept_data["concept_name"],
            first_seen=concept_data["first_seen"] or datetime.utcnow(),
            last_reviewed=concept_data["last_reviewed"] or datetime.utcnow(),
            total_reviews=concept_data["total_reviews"] or 0,
            average_understanding=average_understanding,
            mastery_level=mastery_level,
            retention_strength=retention_strength,
            next_review_date=next_review,
            related_chunks=[p["chunk_id"] for p in chunk_progress]
        )
    
    # ===== Spaced Repetition =====
    
    async def _calculate_next_review(
        self,
        user_id: str,
        concept_id: str,
        performance: float
    ) -> datetime:
        """
        Calculate next review date using SM-2 algorithm.
        
        Args:
            user_id: User ID
            concept_id: Concept ID  
            performance: Performance score (0-1)
            
        Returns:
            Next review date
        """
        # Get current spaced repetition data
        sr_data = await self.db_manager.fetch_one(
            """
            SELECT spaced_repetition_data
            FROM user_concept_progress
            WHERE user_id = $1 AND concept_id = $2
            """,
            user_id, concept_id
        )
        
        if sr_data and sr_data["spaced_repetition_data"]:
            sr = json.loads(sr_data["spaced_repetition_data"])
            interval = sr.get("interval", 1)
            ease_factor = sr.get("ease_factor", self.initial_ease_factor)
            repetitions = sr.get("repetitions", 0)
        else:
            interval = 1
            ease_factor = self.initial_ease_factor
            repetitions = 0
        
        # Convert performance to SM-2 grade (0-5)
        grade = int(performance * 5)
        
        # Update ease factor
        ease_factor = max(
            self.minimum_ease_factor,
            ease_factor + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)
        )
        
        # Calculate new interval
        if grade < 3:
            # Failed - reset
            interval = 1
            repetitions = 0
        else:
            if repetitions == 0:
                interval = 1
            elif repetitions == 1:
                interval = 6
            else:
                interval = int(interval * ease_factor)
            repetitions += 1
        
        # Store updated data
        sr_data_new = {
            "interval": interval,
            "ease_factor": ease_factor,
            "repetitions": repetitions,
            "last_grade": grade
        }
        
        await self.db_manager.execute(
            """
            UPDATE user_concept_progress
            SET spaced_repetition_data = $1
            WHERE user_id = $2 AND concept_id = $3
            """,
            json.dumps(sr_data_new), user_id, concept_id
        )
        
        return datetime.utcnow() + timedelta(days=interval)
    
    async def get_due_reviews(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[ConceptMastery]:
        """
        Get concepts due for review.
        
        Args:
            user_id: User ID
            limit: Maximum number of reviews
            
        Returns:
            List of concepts due for review
        """
        due_concepts = await self.db_manager.fetch_all(
            """
            SELECT concept_id
            FROM user_concept_progress
            WHERE user_id = $1 
                AND next_review_date <= $2
                AND mastery_level < $3
            ORDER BY next_review_date
            LIMIT $4
            """,
            user_id, datetime.utcnow(), self.mastery_threshold, limit
        )
        
        reviews = []
        for concept in due_concepts:
            mastery = await self.calculate_concept_mastery(
                user_id, concept["concept_id"]
            )
            reviews.append(mastery)
        
        return reviews
    
    # ===== Analytics =====
    
    async def get_learning_analytics(
        self,
        user_id: str,
        time_range_days: int = 30
    ) -> LearningAnalytics:
        """
        Get comprehensive learning analytics.
        
        Args:
            user_id: User ID
            time_range_days: Days to analyze
            
        Returns:
            Learning analytics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
        
        # Get overall stats
        overall_stats = await self.db_manager.fetch_one(
            """
            SELECT 
                COUNT(DISTINCT concept_id) as total_concepts,
                SUM(total_time_seconds) / 3600.0 as total_hours,
                AVG(last_understanding_level) as avg_understanding
            FROM user_concept_progress
            WHERE user_id = $1 AND last_reviewed >= $2
            """,
            user_id, cutoff_date
        )
        
        # Get mastered concepts
        mastered = await self.db_manager.fetch_one(
            """
            SELECT COUNT(*) as count
            FROM user_concept_progress  
            WHERE user_id = $1 AND mastery_level >= $2
            """,
            user_id, self.mastery_threshold
        )
        
        # Calculate learning velocity
        sessions = await self.db_manager.fetch_all(
            """
            SELECT end_time, chunks_studied
            FROM learning_sessions
            WHERE user_id = $1 AND end_time >= $2
            ORDER BY end_time
            """,
            user_id, cutoff_date
        )
        
        if sessions and overall_stats["total_hours"]:
            learning_velocity = overall_stats["total_concepts"] / overall_stats["total_hours"]
        else:
            learning_velocity = 0
        
        # Get strengths and weaknesses
        concept_performance = await self.db_manager.fetch_all(
            """
            SELECT c.concept_name, ucp.average_understanding,
                   ucp.mastery_level
            FROM user_concept_progress ucp
            JOIN concepts c ON ucp.concept_id = c.concept_id
            WHERE ucp.user_id = $1
            ORDER BY ucp.average_understanding DESC
            """,
            user_id
        )
        
        strengths = [
            p["concept_name"] for p in concept_performance[:5]
            if p["average_understanding"] >= 0.8
        ]
        
        weaknesses = [
            p["concept_name"] for p in concept_performance
            if p["average_understanding"] < 0.5 and p["average_understanding"] > 0
        ][:5]
        
        # Get retention rate
        retention_data = await self.db_manager.fetch_all(
            """
            SELECT mastery_level, last_reviewed
            FROM user_concept_progress
            WHERE user_id = $1 AND total_reviews > 1
            """,
            user_id
        )
        
        if retention_data:
            retained = sum(
                1 for r in retention_data 
                if r["mastery_level"] >= self.mastery_threshold * 0.8
            )
            retention_rate = retained / len(retention_data)
        else:
            retention_rate = 0
        
        # Get recommended reviews
        due_reviews = await self.get_due_reviews(user_id, limit=5)
        recommended_review = [r.concept_name for r in due_reviews]
        
        return LearningAnalytics(
            total_study_time_hours=overall_stats["total_hours"] or 0,
            total_concepts_studied=overall_stats["total_concepts"] or 0,
            concepts_mastered=mastered["count"] or 0,
            average_understanding=overall_stats["avg_understanding"] or 0,
            learning_velocity=learning_velocity,
            retention_rate=retention_rate,
            strengths=strengths,
            weaknesses=weaknesses,
            recommended_review=recommended_review
        )
    
    async def get_learning_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get learning trends over time.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dictionary of trend data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily progress
        daily_progress = await self.db_manager.fetch_all(
            """
            SELECT 
                DATE(timestamp) as date,
                COUNT(DISTINCT chunk_id) as chunks_studied,
                SUM(time_spent_seconds) / 3600.0 as hours_studied,
                AVG(understanding_level) as avg_understanding
            FROM session_progress sp
            JOIN learning_sessions ls ON sp.session_id = ls.session_id
            WHERE ls.user_id = $1 AND sp.timestamp >= $2
            GROUP BY DATE(timestamp)
            ORDER BY date
            """,
            user_id, cutoff_date
        )
        
        # Concept mastery progression
        mastery_progression = await self.db_manager.fetch_all(
            """
            SELECT 
                DATE(last_reviewed) as date,
                COUNT(CASE WHEN mastery_level >= $2 THEN 1 END) as mastered,
                COUNT(*) as total
            FROM user_concept_progress
            WHERE user_id = $1 AND last_reviewed >= $3
            GROUP BY DATE(last_reviewed)
            ORDER BY date
            """,
            user_id, self.mastery_threshold, cutoff_date
        )
        
        return {
            "daily_progress": [
                {
                    "date": p["date"].isoformat(),
                    "chunks_studied": p["chunks_studied"],
                    "hours_studied": round(p["hours_studied"], 2),
                    "avg_understanding": round(p["avg_understanding"], 2)
                }
                for p in daily_progress
            ],
            "mastery_progression": [
                {
                    "date": m["date"].isoformat(),
                    "mastered": m["mastered"],
                    "total": m["total"],
                    "mastery_rate": round(m["mastered"] / m["total"], 2) if m["total"] > 0 else 0
                }
                for m in mastery_progression
            ]
        }
    
    # ===== Recommendations =====
    
    async def get_adaptive_recommendations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get adaptive learning recommendations.
        
        Considers:
        - Current mastery levels
        - Learning velocity
        - Prerequisite satisfaction
        - Difficulty progression
        - Time since last review
        
        Args:
            user_id: User ID
            limit: Number of recommendations
            
        Returns:
            List of recommended chunks with reasoning
        """
        # Get user's current level and progress
        user_stats = await self.get_learning_analytics(user_id)
        
        # Get concepts in progress
        in_progress = await self.db_manager.fetch_all(
            """
            SELECT concept_id, average_understanding, mastery_level
            FROM user_concept_progress
            WHERE user_id = $1 
                AND mastery_level < $2
                AND average_understanding > 0.2
            ORDER BY last_reviewed DESC
            LIMIT 20
            """,
            user_id, self.mastery_threshold
        )
        
        # Get prerequisite data
        prerequisites = await self.db_manager.fetch_all(
            """
            SELECT cp.concept_id, cp.prerequisite_id, 
                   ucp.mastery_level as prereq_mastery
            FROM concept_prerequisites cp
            LEFT JOIN user_concept_progress ucp
                ON cp.prerequisite_id = ucp.concept_id AND ucp.user_id = $1
            """,
            user_id
        )
        
        # Build prerequisite map
        prereq_map = defaultdict(list)
        for p in prerequisites:
            prereq_map[p["concept_id"]].append({
                "id": p["prerequisite_id"],
                "mastery": p["prereq_mastery"] or 0
            })
        
        recommendations = []
        
        # 1. Due reviews (highest priority)
        due_reviews = await self.get_due_reviews(user_id, limit=limit // 2)
        for review in due_reviews:
            # Get best chunk for this concept
            chunk = await self._get_best_chunk_for_concept(
                user_id, review.concept_id
            )
            if chunk:
                recommendations.append({
                    "chunk_id": chunk["chunk_id"],
                    "concept_id": review.concept_id,
                    "concept_name": review.concept_name,
                    "reason": "Due for spaced repetition review",
                    "priority": "high",
                    "difficulty": chunk["difficulty"],
                    "estimated_time": chunk["estimated_time"],
                    "prerequisites_met": True
                })
        
        # 2. Continue in-progress concepts
        for concept in in_progress:
            if len(recommendations) >= limit:
                break
                
            # Check prerequisites
            concept_prereqs = prereq_map.get(concept["concept_id"], [])
            prereqs_met = all(
                p["mastery"] >= self.mastery_threshold * 0.7 
                for p in concept_prereqs
            )
            
            if prereqs_met:
                chunk = await self._get_next_chunk_for_concept(
                    user_id, concept["concept_id"]
                )
                if chunk:
                    recommendations.append({
                        "chunk_id": chunk["chunk_id"],
                        "concept_id": concept["concept_id"],
                        "concept_name": chunk["concept_name"],
                        "reason": "Continue learning in-progress concept",
                        "priority": "medium",
                        "difficulty": chunk["difficulty"],
                        "estimated_time": chunk["estimated_time"],
                        "prerequisites_met": True
                    })
        
        # 3. New concepts with met prerequisites
        if len(recommendations) < limit:
            new_concepts = await self._get_recommended_new_concepts(
                user_id, limit - len(recommendations)
            )
            
            for concept in new_concepts:
                chunk = await self._get_best_chunk_for_concept(
                    user_id, concept["concept_id"]
                )
                if chunk:
                    recommendations.append({
                        "chunk_id": chunk["chunk_id"],
                        "concept_id": concept["concept_id"],
                        "concept_name": concept["concept_name"],
                        "reason": concept["reason"],
                        "priority": "low",
                        "difficulty": chunk["difficulty"],
                        "estimated_time": chunk["estimated_time"],
                        "prerequisites_met": True
                    })
        
        return recommendations[:limit]
    
    # ===== Helper Methods =====
    
    async def _create_tables(self) -> None:
        """Create necessary tables for learning progress tracking"""
        await self.db_manager.execute_many([
            """
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                total_time_seconds INTEGER DEFAULT 0,
                chunks_studied INTEGER DEFAULT 0,
                average_understanding FLOAT DEFAULT 0,
                metadata JSONB DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS session_progress (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                chunk_id VARCHAR(255) NOT NULL,
                time_spent_seconds INTEGER NOT NULL,
                understanding_level FLOAT NOT NULL,
                interaction_data JSONB DEFAULT '{}',
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_chunk_progress (
                user_id VARCHAR(255) NOT NULL,
                chunk_id VARCHAR(255) NOT NULL,
                total_time_seconds INTEGER DEFAULT 0,
                last_understanding_level FLOAT,
                review_count INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                PRIMARY KEY (user_id, chunk_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_concept_progress (
                user_id VARCHAR(255) NOT NULL,
                concept_id VARCHAR(255) NOT NULL,
                first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
                last_reviewed TIMESTAMP,
                total_reviews INTEGER DEFAULT 0,
                average_understanding FLOAT DEFAULT 0,
                mastery_level FLOAT DEFAULT 0,
                next_review_date TIMESTAMP,
                spaced_repetition_data JSONB DEFAULT '{}',
                PRIMARY KEY (user_id, concept_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS concepts (
                concept_id VARCHAR(255) PRIMARY KEY,
                concept_name VARCHAR(500) NOT NULL,
                subject VARCHAR(255),
                difficulty_level FLOAT,
                metadata JSONB DEFAULT '{}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS concept_chunks (
                concept_id VARCHAR(255) NOT NULL,
                chunk_id VARCHAR(255) NOT NULL,
                relevance_score FLOAT DEFAULT 1.0,
                PRIMARY KEY (concept_id, chunk_id),
                FOREIGN KEY (concept_id) REFERENCES concepts(concept_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS concept_prerequisites (
                concept_id VARCHAR(255) NOT NULL,
                prerequisite_id VARCHAR(255) NOT NULL,
                importance FLOAT DEFAULT 1.0,
                PRIMARY KEY (concept_id, prerequisite_id),
                FOREIGN KEY (concept_id) REFERENCES concepts(concept_id),
                FOREIGN KEY (prerequisite_id) REFERENCES concepts(concept_id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_session_progress_session 
                ON session_progress(session_id);
            CREATE INDEX IF NOT EXISTS idx_session_progress_timestamp 
                ON session_progress(timestamp);
            CREATE INDEX IF NOT EXISTS idx_user_chunk_progress_user 
                ON user_chunk_progress(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_concept_progress_user 
                ON user_concept_progress(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_concept_next_review 
                ON user_concept_progress(user_id, next_review_date);
            """
        ])
    
    async def _get_chunk_concepts(self, chunk_id: str) -> List[str]:
        """Get concepts associated with a chunk"""
        # First try database
        concepts = await self.db_manager.fetch_all(
            """
            SELECT concept_id FROM concept_chunks
            WHERE chunk_id = $1
            """,
            chunk_id
        )
        
        if concepts:
            return [c["concept_id"] for c in concepts]
        
        # Fallback to Neo4j
        query = """
        MATCH (c:Chunk {chunk_id: $chunk_id})-[:MENTIONS_CONCEPT]->(concept:Concept)
        RETURN concept.concept_id as concept_id
        """
        
        results = await self.neo4j_search.connection_manager.execute_query(
            query, {"chunk_id": chunk_id}
        )
        
        return [r["concept_id"] for r in results]
    
    async def _update_concept_progress(
        self,
        user_id: str,
        concept_id: str,
        understanding_level: float
    ) -> None:
        """Update progress for a concept"""
        await self.db_manager.execute(
            """
            INSERT INTO user_concept_progress
            (user_id, concept_id, first_seen, last_reviewed, 
             total_reviews, average_understanding)
            VALUES ($1, $2, $3, $3, 1, $4)
            ON CONFLICT (user_id, concept_id)
            DO UPDATE SET
                last_reviewed = $3,
                total_reviews = user_concept_progress.total_reviews + 1,
                average_understanding = (
                    user_concept_progress.average_understanding * 
                    user_concept_progress.total_reviews + $4
                ) / (user_concept_progress.total_reviews + 1)
            """,
            user_id, concept_id, datetime.utcnow(), understanding_level
        )
        
        # Recalculate mastery
        mastery = await self.calculate_concept_mastery(user_id, concept_id)
        
        await self.db_manager.execute(
            """
            UPDATE user_concept_progress
            SET mastery_level = $1, next_review_date = $2
            WHERE user_id = $3 AND concept_id = $4
            """,
            mastery.mastery_level, mastery.next_review_date,
            user_id, concept_id
        )
    
    async def _get_best_chunk_for_concept(
        self,
        user_id: str,
        concept_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the best chunk to study for a concept"""
        # Get chunks not yet studied or with low understanding
        query = """
        MATCH (concept:Concept {concept_id: $concept_id})
        MATCH (concept)<-[:MENTIONS_CONCEPT]-(chunk:Chunk)
        OPTIONAL MATCH (user:User {user_id: $user_id})
        OPTIONAL MATCH (user)-[studied:STUDIED]->(chunk)
        WITH chunk, concept,
             COALESCE(studied.understanding_level, 0) as understanding,
             COALESCE(studied.review_count, 0) as reviews
        WHERE understanding < 0.7 OR reviews = 0
        RETURN chunk.chunk_id as chunk_id,
               chunk.difficulty_score as difficulty,
               chunk.word_count as word_count,
               concept.name as concept_name,
               understanding, reviews
        ORDER BY reviews ASC, understanding ASC
        LIMIT 1
        """
        
        results = await self.neo4j_search.connection_manager.execute_query(
            query, {"concept_id": concept_id, "user_id": user_id}
        )
        
        if results:
            result = results[0]
            # Estimate reading time (200 words per minute)
            estimated_time = max(1, result["word_count"] // 200)
            
            return {
                "chunk_id": result["chunk_id"],
                "difficulty": result["difficulty"],
                "estimated_time": estimated_time,
                "concept_name": result["concept_name"]
            }
        
        return None
    
    async def _get_next_chunk_for_concept(
        self,
        user_id: str,
        concept_id: str  
    ) -> Optional[Dict[str, Any]]:
        """Get next unvisited chunk for concept"""
        return await self._get_best_chunk_for_concept(user_id, concept_id)
    
    async def _get_recommended_new_concepts(
        self,
        user_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get new concepts ready to learn"""
        # Get concepts where prerequisites are met
        query = """
        WITH user_mastery AS (
            SELECT concept_id, mastery_level
            FROM user_concept_progress
            WHERE user_id = $1
        )
        SELECT DISTINCT c.concept_id, c.concept_name,
               c.difficulty_level,
               COUNT(cp.prerequisite_id) as total_prereqs,
               COUNT(um.concept_id) as met_prereqs
        FROM concepts c
        LEFT JOIN concept_prerequisites cp ON c.concept_id = cp.concept_id
        LEFT JOIN user_mastery um ON cp.prerequisite_id = um.concept_id 
                                  AND um.mastery_level >= $2
        WHERE c.concept_id NOT IN (
            SELECT concept_id FROM user_concept_progress WHERE user_id = $1
        )
        GROUP BY c.concept_id, c.concept_name, c.difficulty_level
        HAVING COUNT(cp.prerequisite_id) = 0 
            OR COUNT(um.concept_id) >= COUNT(cp.prerequisite_id) * 0.7
        ORDER BY c.difficulty_level ASC
        LIMIT $3
        """
        
        results = await self.db_manager.fetch_all(
            query, user_id, self.mastery_threshold * 0.7, limit
        )
        
        recommendations = []
        for r in results:
            reason = "New concept with prerequisites met"
            if r["total_prereqs"] == 0:
                reason = "Foundational concept - no prerequisites"
            elif r["met_prereqs"] == r["total_prereqs"]:
                reason = "All prerequisites mastered"
                
            recommendations.append({
                "concept_id": r["concept_id"],
                "concept_name": r["concept_name"],
                "reason": reason
            })
        
        return recommendations