#!/usr/bin/env python3
"""
Integration Test Script for LearnTrac API

Tests the complete flow from PDF processing to recommendations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.database import DatabaseManager
from src.services.redis_client import RedisCache
from src.services.embedding_service import EmbeddingService
from src.pdf_processing.pipeline import PDFProcessingPipeline
from src.pdf_processing.content_chunker import ContentChunker
from src.pdf_processing.embedding_generator import EmbeddingGenerator
from src.pdf_processing.embedding_pipeline import EmbeddingPipeline
from src.pdf_processing.neo4j_connection_manager import ConnectionConfig
from src.pdf_processing.neo4j_content_ingestion import Neo4jContentIngestion, TextbookMetadata
from src.pdf_processing.neo4j_search import Neo4jVectorSearch
from src.services.trac_service import TracService
from src.services.auth_service import AuthService
from src.services.learning_progress_tracker import LearningProgressTracker
from src.services.recommendation_engine import RecommendationEngine
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_integration():
    """Test the complete integration flow"""
    logger.info("Starting integration test...")
    
    # Initialize components
    logger.info("Initializing components...")
    
    # Database
    db_manager = DatabaseManager(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "learntrac"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )
    await db_manager.initialize()
    
    # Redis
    redis_cache = RedisCache(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379))
    )
    await redis_cache.initialize()
    
    # Embedding service
    embedding_service = EmbeddingService(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        cache_client=redis_cache
    )
    await embedding_service.initialize()
    
    # Neo4j config
    neo4j_config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USERNAME", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    # Initialize services
    logger.info("Initializing services...")
    
    # PDF processing pipeline
    pdf_pipeline = PDFProcessingPipeline()
    content_chunker = ContentChunker()
    embedding_generator = EmbeddingGenerator(cache_manager=redis_cache)
    embedding_pipeline = EmbeddingPipeline(
        generator=embedding_generator,
        cache_manager=redis_cache
    )
    
    # Neo4j services
    neo4j_ingestion = Neo4jContentIngestion(neo4j_config)
    await neo4j_ingestion.initialize()
    
    neo4j_search = Neo4jVectorSearch(neo4j_config)
    await neo4j_search.initialize()
    
    # Auth service
    auth_service = AuthService(db_manager, redis_cache)
    await auth_service.initialize()
    
    # Progress tracker
    progress_tracker = LearningProgressTracker(
        db_manager, redis_cache, neo4j_search
    )
    await progress_tracker.initialize()
    
    # Recommendation engine
    recommendation_engine = RecommendationEngine(
        db_manager, redis_cache, neo4j_search,
        progress_tracker, embedding_service
    )
    await recommendation_engine.initialize()
    
    # Trac service
    trac_service = TracService(
        db_manager, neo4j_config, redis_cache, embedding_service
    )
    await trac_service.initialize()
    
    logger.info("All components initialized successfully!")
    
    # Test flow
    try:
        # 1. Create test user
        logger.info("\n1. Creating test user...")
        user = await auth_service.register_user(
            email="test@example.com",
            username="testuser",
            password="TestPass123!",
            full_name="Test User",
            role="student"
        )
        
        if user:
            logger.info(f"Created user: {user.username} ({user.id})")
        else:
            logger.info("User already exists")
            user = await auth_service.authenticate_user("test@example.com", "TestPass123!")
        
        # 2. Process a sample PDF (if available)
        pdf_path = "textbooks/Introduction_To_Computer_Science.pdf"
        if os.path.exists(pdf_path):
            logger.info(f"\n2. Processing PDF: {pdf_path}")
            
            metadata = TextbookMetadata(
                textbook_id="cs101",
                title="Introduction to Computer Science",
                subject="Computer Science",
                authors=["Test Author"],
                source_file=pdf_path,
                processing_date=datetime.utcnow(),
                processing_version="1.0"
            )
            
            result = await trac_service.ingest_textbook(pdf_path, metadata)
            logger.info(f"Ingestion result: {result}")
        else:
            logger.info(f"\n2. PDF not found at {pdf_path}, skipping ingestion")
        
        # 3. Test search
        logger.info("\n3. Testing content search...")
        search_results = await trac_service.search_content(
            query="data structures",
            user_id=user.id,
            limit=5
        )
        logger.info(f"Found {len(search_results.results)} results")
        for i, result in enumerate(search_results.results[:3]):
            logger.info(f"  {i+1}. Score: {result.score:.3f} - {result.chunk_metadata.content_type}")
        
        # 4. Test progress tracking
        logger.info("\n4. Testing progress tracking...")
        session_id = await progress_tracker.start_session(user.id)
        logger.info(f"Started session: {session_id}")
        
        if search_results.results:
            # Track progress on first result
            chunk = search_results.results[0]
            await progress_tracker.track_chunk_progress(
                session_id=session_id,
                chunk_id=chunk.chunk_id,
                time_spent_seconds=120,
                understanding_level=0.75
            )
            logger.info(f"Tracked progress on chunk {chunk.chunk_id}")
        
        # End session
        session = await progress_tracker.end_session(session_id)
        logger.info(f"Session ended - duration: {session.total_time_seconds}s")
        
        # 5. Test recommendations
        logger.info("\n5. Testing recommendations...")
        recommendations = await recommendation_engine.get_recommendations(
            user_id=user.id,
            limit=5
        )
        logger.info(f"Got {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations[:3]):
            logger.info(f"  {i+1}. {rec.concept_name} - Score: {rec.score:.3f}")
            logger.info(f"     Reason: {rec.reason}")
        
        # 6. Test learning analytics
        logger.info("\n6. Testing learning analytics...")
        analytics = await progress_tracker.get_learning_analytics(user.id)
        logger.info(f"Learning Analytics:")
        logger.info(f"  Total study time: {analytics.total_study_time_hours:.1f} hours")
        logger.info(f"  Concepts studied: {analytics.total_concepts_studied}")
        logger.info(f"  Average understanding: {analytics.average_understanding:.1%}")
        
        logger.info("\n✅ Integration test completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Integration test failed: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("\nCleaning up...")
        await db_manager.close()
        await redis_cache.close()
        await neo4j_ingestion.close()
        await neo4j_search.close()


if __name__ == "__main__":
    asyncio.run(test_integration())