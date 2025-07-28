#!/usr/bin/env python3
"""
Test Neo4j Chunks Retrieval and Learning Path Processing

This script connects directly to Neo4j to retrieve actual chunks
and tests the learning path creation workflow.
"""

import asyncio
import asyncpg
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import sys
import os

# Add the learntrac-api src directory to the path
sys.path.append('/Users/hutch/Documents/projects/gauntlet/p6/trac/learntrac/learntrac-api/src')

from services.neo4j_aura_client import neo4j_aura_client
from services.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jChunkTester:
    """Tests Neo4j chunk retrieval and processing"""
    
    def __init__(self):
        self.db_connection = None
        self.embedding_service = EmbeddingService()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "neo4j_health": {},
            "chunks_retrieved": [],
            "vector_search_test": {},
            "database_state": {},
            "errors": []
        }
    
    async def connect_to_database(self):
        """Connect to RDS PostgreSQL database"""
        try:
            self.db_connection = await asyncpg.connect(
                host="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com",
                port=5432,
                user="learntrac_admin", 
                password="Vp-Sl}}D[(j&zxP5cjh%MTQtitYq2ic7",
                database="learntrac",
                ssl="require"
            )
            logger.info("Connected to RDS PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self.test_results["errors"].append(f"Database connection failed: {e}")
            return False
    
    async def test_neo4j_health(self):
        """Test Neo4j connectivity and get health status"""
        try:
            health_status = await neo4j_aura_client.health_check()
            self.test_results["neo4j_health"] = health_status
            
            logger.info(f"Neo4j Health Status: {health_status.get('status', 'unknown')}")
            if health_status.get('chunk_count'):
                logger.info(f"Neo4j Chunk Count: {health_status['chunk_count']}")
            
            return health_status.get('status') == 'healthy'
            
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            self.test_results["errors"].append(f"Neo4j health check failed: {e}")
            return False
    
    async def retrieve_sample_chunks(self) -> List[Dict[str, Any]]:
        """Retrieve sample chunks directly from Neo4j"""
        try:
            # Get a sample query embedding
            sample_query = "computer science algorithms and data structures"
            query_embedding = await self.embedding_service.get_embedding(sample_query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            logger.info(f"Generated embedding for query: '{sample_query}'")
            logger.info(f"Embedding dimension: {len(query_embedding)}")
            
            # Perform vector search to get actual chunks
            chunks = await neo4j_aura_client.vector_search(
                embedding=query_embedding,
                min_score=0.6,  # Lower threshold to get more results
                limit=20
            )
            
            self.test_results["chunks_retrieved"] = chunks
            self.test_results["vector_search_test"] = {
                "query": sample_query,
                "embedding_dim": len(query_embedding),
                "min_score": 0.6,
                "chunks_found": len(chunks)
            }
            
            logger.info(f"Retrieved {len(chunks)} chunks from Neo4j")
            
            # Log first few chunks for verification
            for i, chunk in enumerate(chunks[:3]):
                logger.info(f"Chunk {i+1}: {chunk.get('concept', 'N/A')} (Score: {chunk.get('score', 'N/A'):.3f})")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks from Neo4j: {e}")
            self.test_results["errors"].append(f"Failed to retrieve chunks: {e}")
            return []
    
    async def analyze_chunk_data(self, chunks: List[Dict[str, Any]]):
        """Analyze the structure and content of retrieved chunks"""
        if not chunks:
            logger.warning("No chunks to analyze")
            return
        
        analysis = {
            "total_chunks": len(chunks),
            "score_range": {
                "min": min(chunk.get('score', 0) for chunk in chunks),
                "max": max(chunk.get('score', 0) for chunk in chunks),
                "avg": sum(chunk.get('score', 0) for chunk in chunks) / len(chunks)
            },
            "subjects": list(set(chunk.get('subject', 'Unknown') for chunk in chunks)),
            "concepts": list(set(chunk.get('concept', 'Unknown') for chunk in chunks)),
            "with_prerequisites": sum(1 for chunk in chunks if chunk.get('has_prerequisite')),
            "prerequisite_for_others": sum(1 for chunk in chunks if chunk.get('prerequisite_for'))
        }
        
        self.test_results["chunk_analysis"] = analysis
        
        logger.info(f"Chunk Analysis:")
        logger.info(f"  - Total chunks: {analysis['total_chunks']}")
        logger.info(f"  - Score range: {analysis['score_range']['min']:.3f} - {analysis['score_range']['max']:.3f}")
        logger.info(f"  - Average score: {analysis['score_range']['avg']:.3f}")
        logger.info(f"  - Unique subjects: {len(analysis['subjects'])}")
        logger.info(f"  - Unique concepts: {len(analysis['concepts'])}")
        logger.info(f"  - With prerequisites: {analysis['with_prerequisites']}")
        
        # Show sample subjects and concepts
        logger.info(f"  - Sample subjects: {analysis['subjects'][:5]}")
        logger.info(f"  - Sample concepts: {analysis['concepts'][:5]}")
    
    async def simulate_learning_path_creation(self, chunks: List[Dict[str, Any]]):
        """Simulate the learning path creation process with actual chunk data"""
        if not chunks:
            logger.warning("No chunks available for learning path simulation")
            return
        
        try:
            # Transform chunks to the format expected by the learning path API
            transformed_chunks = []
            for chunk in chunks:
                transformed_chunk = {
                    "id": chunk.get("id", f"chunk_{len(transformed_chunks)}"),
                    "content": chunk.get("content", "No content available"),
                    "concept": chunk.get("concept", "Unknown Concept"),
                    "subject": chunk.get("subject", "General"),
                    "score": chunk.get("score", 0.0),
                    "has_prerequisite": chunk.get("has_prerequisite"),
                    "prerequisite_for": chunk.get("prerequisite_for"),
                    "metadata": {
                        "source": "vector_search",
                        "search_score": chunk.get("score", 0.0)
                    }
                }
                transformed_chunks.append(transformed_chunk)
            
            # Simulate the learning path creation
            learning_path_simulation = {
                "input_data": {
                    "query": "computer science algorithms and data structures",
                    "min_score": 0.6,
                    "max_chunks": len(chunks),
                    "path_title": "CS Fundamentals Learning Path",
                    "difficulty_level": "intermediate"
                },
                "processed_chunks": transformed_chunks,
                "simulated_output": {
                    "path_id": "12345678-1234-5678-9abc-123456789012",
                    "message": f"Successfully created learning path with {len(chunks)} concepts",
                    "ticket_count": len(chunks),
                    "prerequisite_count": sum(1 for chunk in chunks if chunk.get("has_prerequisite"))
                }
            }
            
            self.test_results["learning_path_simulation"] = learning_path_simulation
            
            logger.info(f"Learning Path Simulation:")
            logger.info(f"  - Input chunks: {len(chunks)}")
            logger.info(f"  - Transformed chunks: {len(transformed_chunks)}")
            logger.info(f"  - Simulated tickets: {learning_path_simulation['simulated_output']['ticket_count']}")
            logger.info(f"  - Prerequisites: {learning_path_simulation['simulated_output']['prerequisite_count']}")
            
        except Exception as e:
            logger.error(f"Learning path simulation failed: {e}")
            self.test_results["errors"].append(f"Learning path simulation failed: {e}")
    
    async def check_database_state(self):
        """Check current database state"""
        if not self.db_connection:
            logger.error("No database connection available")
            return
        
        try:
            database_state = {}
            
            # Check learning paths
            paths = await self.db_connection.fetch("""
                SELECT id, title, cognito_user_id, created_at, total_chunks 
                FROM learning.paths 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            database_state["recent_paths"] = [dict(row) for row in paths]
            
            # Check concept metadata
            concepts = await self.db_connection.fetch("""
                SELECT ticket_id, path_id, chunk_id, relevance_score, created_at
                FROM learning.concept_metadata 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            database_state["recent_concepts"] = [dict(row) for row in concepts]
            
            # Check tickets
            tickets = await self.db_connection.fetch("""
                SELECT id, type, summary, owner, time
                FROM public.ticket 
                WHERE type = 'learning_concept'
                ORDER BY time DESC 
                LIMIT 5
            """)
            database_state["recent_learning_tickets"] = [dict(row) for row in tickets]
            
            # Table counts
            counts = {}
            for table in ["paths", "concept_metadata", "prerequisites", "progress"]:
                count = await self.db_connection.fetchval(f"SELECT COUNT(*) FROM learning.{table}")
                counts[table] = count
            
            database_state["table_counts"] = counts
            
            self.test_results["database_state"] = database_state
            
            logger.info(f"Database State:")
            logger.info(f"  - Recent paths: {len(database_state['recent_paths'])}")
            logger.info(f"  - Recent concepts: {len(database_state['recent_concepts'])}")
            logger.info(f"  - Recent learning tickets: {len(database_state['recent_learning_tickets'])}")
            logger.info(f"  - Table counts: {counts}")
            
        except Exception as e:
            logger.error(f"Database state check failed: {e}")
            self.test_results["errors"].append(f"Database state check failed: {e}")
    
    def save_results(self):
        """Save test results to JSON file"""
        filename = f"neo4j_chunk_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to {filename}")
        return filename
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("NEO4J CHUNKS AND LEARNING PATH TEST SUMMARY")
        print("="*80)
        
        neo4j_status = self.test_results.get("neo4j_health", {}).get("status", "unknown")
        chunks_count = len(self.test_results.get("chunks_retrieved", []))
        errors_count = len(self.test_results.get("errors", []))
        
        print(f"\n📊 TEST RESULTS:")
        print(f"   - Neo4j Status: {neo4j_status}")
        print(f"   - Chunks Retrieved: {chunks_count}")
        print(f"   - Database Connected: {'✅' if self.db_connection else '❌'}")
        print(f"   - Errors: {errors_count}")
        
        # Neo4j details
        neo4j_health = self.test_results.get("neo4j_health", {})
        if neo4j_health:
            print(f"\n🗄️ NEO4J STATUS:")
            print(f"   - Status: {neo4j_health.get('status', 'unknown')}")
            if 'chunk_count' in neo4j_health:
                print(f"   - Total chunks in DB: {neo4j_health['chunk_count']}")
            if 'gds_version' in neo4j_health:
                print(f"   - GDS Version: {neo4j_health['gds_version']}")
        
        # Chunk analysis
        chunk_analysis = self.test_results.get("chunk_analysis", {})
        if chunk_analysis:
            print(f"\n📋 CHUNK ANALYSIS:")
            print(f"   - Total retrieved: {chunk_analysis['total_chunks']}")
            print(f"   - Score range: {chunk_analysis['score_range']['min']:.3f} - {chunk_analysis['score_range']['max']:.3f}")
            print(f"   - Average score: {chunk_analysis['score_range']['avg']:.3f}")
            print(f"   - Unique subjects: {len(chunk_analysis['subjects'])}")
            print(f"   - Unique concepts: {len(chunk_analysis['concepts'])}")
            print(f"   - With prerequisites: {chunk_analysis['with_prerequisites']}")
        
        # Learning path simulation
        simulation = self.test_results.get("learning_path_simulation", {})
        if simulation:
            simulated_output = simulation.get("simulated_output", {})
            print(f"\n🎯 LEARNING PATH SIMULATION:")
            print(f"   - Path ID: {simulated_output.get('path_id', 'N/A')}")
            print(f"   - Ticket count: {simulated_output.get('ticket_count', 'N/A')}")
            print(f"   - Prerequisites: {simulated_output.get('prerequisite_count', 'N/A')}")
        
        # Database state
        db_state = self.test_results.get("database_state", {})
        if db_state:
            counts = db_state.get("table_counts", {})
            print(f"\n💾 DATABASE STATE:")
            for table, count in counts.items():
                print(f"   - {table}: {count} records")
        
        # Errors
        if errors_count > 0:
            print(f"\n❌ ERRORS:")
            for error in self.test_results["errors"]:
                print(f"   - {error}")
        
        # Sample chunks
        chunks = self.test_results.get("chunks_retrieved", [])
        if chunks:
            print(f"\n📄 SAMPLE CHUNKS:")
            for i, chunk in enumerate(chunks[:3]):
                print(f"   {i+1}. Concept: {chunk.get('concept', 'N/A')}")
                print(f"      Subject: {chunk.get('subject', 'N/A')}")
                print(f"      Score: {chunk.get('score', 'N/A'):.3f}")
                print(f"      Content: {chunk.get('content', 'N/A')[:100]}...")
        
        print(f"\n🔧 NEXT STEPS:")
        if neo4j_status == "healthy" and chunks_count > 0:
            print(f"   ✅ Neo4j is working and has chunks available")
            print(f"   ✅ Vector search functionality is operational")
            print(f"   🔧 Ready for full learning path API integration")
        else:
            print(f"   🔧 Check Neo4j connectivity and configuration")
            print(f"   🔧 Verify chunk data exists in Neo4j")
            print(f"   🔧 Test embedding service configuration")
    
    async def run_test(self):
        """Run the complete Neo4j chunk test"""
        logger.info("Starting Neo4j chunk retrieval and processing test...")
        
        try:
            # Step 1: Connect to database
            if not await self.connect_to_database():
                logger.error("Cannot proceed without database connection")
                return False
            
            # Step 2: Test Neo4j health
            neo4j_healthy = await self.test_neo4j_health()
            
            # Step 3: Retrieve sample chunks
            chunks = await self.retrieve_sample_chunks()
            
            # Step 4: Analyze chunk data
            await self.analyze_chunk_data(chunks)
            
            # Step 5: Simulate learning path creation
            await self.simulate_learning_path_creation(chunks)
            
            # Step 6: Check database state
            await self.check_database_state()
            
            # Step 7: Generate reports
            results_file = self.save_results()
            self.print_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Neo4j chunk test failed: {e}")
            self.test_results["errors"].append(f"Test execution failed: {e}")
            return False
            
        finally:
            if self.db_connection:
                await self.db_connection.close()
                logger.info("Database connection closed")


async def main():
    """Main function"""
    tester = Neo4jChunkTester()
    success = await tester.run_test()
    
    if success:
        print(f"\n✅ Neo4j chunk test completed")
    else:
        print(f"\n❌ Neo4j chunk test failed")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))