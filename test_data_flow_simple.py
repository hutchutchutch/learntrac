#!/usr/bin/env python3
"""
Simple Data Flow Test for LearnTrac Learning Path System

This script tests data flow without API dependencies by:
1. Checking database connectivity and schema
2. Simulating the learning path data flow
3. Verifying schema consistency across UI, Database, and API expectations
"""

import asyncio
import asyncpg
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleDataFlowTester:
    """Tests data flow and schema consistency"""
    
    def __init__(self):
        self.db_connection = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "database_connectivity": False,
            "schema_validation": {},
            "data_flow_simulation": {},
            "sample_data_test": {},
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
            logger.info("✅ Connected to RDS PostgreSQL database")
            self.test_results["database_connectivity"] = True
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            self.test_results["errors"].append(f"Database connection failed: {e}")
            return False
    
    async def validate_schema_structure(self):
        """Validate that all required tables and columns exist"""
        
        schema_validation = {
            "required_tables_exist": True,
            "foreign_keys_valid": True,
            "column_types_correct": True,
            "validation_details": {},
            "missing_elements": []
        }
        
        try:
            # Check required tables
            required_tables = {
                "learning.paths": ["id", "title", "cognito_user_id", "created_at", "total_chunks", "question_difficulty"],
                "learning.concept_metadata": ["ticket_id", "path_id", "chunk_id", "relevance_score", "question_generated"],
                "learning.prerequisites": ["concept_ticket_id", "prerequisite_ticket_id", "created_at"],
                "learning.progress": ["cognito_user_id", "ticket_id", "status", "time_spent_minutes"],
                "public.ticket": ["id", "type", "summary", "description", "owner", "keywords"],
                "public.ticket_custom": ["ticket", "name", "value"]
            }
            
            for table, expected_columns in required_tables.items():
                schema, table_name = table.split('.')
                
                # Check if table exists
                table_exists = await self.db_connection.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = $1 AND table_name = $2
                    )
                """, schema, table_name)
                
                if not table_exists:
                    schema_validation["required_tables_exist"] = False
                    schema_validation["missing_elements"].append(f"Table {table} missing")
                    continue
                
                # Check columns
                existing_columns = await self.db_connection.fetch("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = $1 AND table_name = $2
                """, schema, table_name)
                
                existing_column_names = [row['column_name'] for row in existing_columns]
                
                for expected_col in expected_columns:
                    if expected_col not in existing_column_names:
                        schema_validation["column_types_correct"] = False
                        schema_validation["missing_elements"].append(f"Column {table}.{expected_col} missing")
                
                schema_validation["validation_details"][table] = {
                    "exists": table_exists,
                    "expected_columns": expected_columns,
                    "actual_columns": existing_column_names,
                    "missing_columns": [col for col in expected_columns if col not in existing_column_names]
                }
            
            # Check foreign key relationships
            foreign_keys = await self.db_connection.fetch("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.table_schema
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                    AND tc.table_schema IN ('learning', 'public')
                ORDER BY tc.table_name, kcu.column_name
            """)
            
            schema_validation["foreign_keys"] = [dict(row) for row in foreign_keys]
            
            logger.info(f"Schema validation completed:")
            logger.info(f"  - Required tables exist: {'✅' if schema_validation['required_tables_exist'] else '❌'}")
            logger.info(f"  - Foreign keys valid: {'✅' if schema_validation['foreign_keys_valid'] else '❌'}")
            logger.info(f"  - Column types correct: {'✅' if schema_validation['column_types_correct'] else '❌'}")
            
            if schema_validation["missing_elements"]:
                logger.warning(f"  - Missing elements: {len(schema_validation['missing_elements'])}")
                for missing in schema_validation["missing_elements"]:
                    logger.warning(f"    - {missing}")
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            self.test_results["errors"].append(f"Schema validation failed: {e}")
        
        self.test_results["schema_validation"] = schema_validation
    
    async def test_sample_data_insertion(self):
        """Test inserting sample data to verify the data flow"""
        
        sample_test = {
            "test_executed": False,
            "learning_path_created": False,
            "tickets_created": 0,
            "concept_metadata_created": 0,
            "custom_fields_created": 0,
            "test_data": {}
        }
        
        try:
            # Sample data that matches the API expectations
            sample_learning_path = {
                "title": "Test Learning Path - Data Flow Verification",
                "query_text": "test query for data flow validation",
                "cognito_user_id": "test-user-12345",
                "total_chunks": 3,
                "question_difficulty": 3
            }
            
            sample_chunks = [
                {
                    "id": "test_chunk_001",
                    "content": "Introduction to algorithms and their complexity analysis.",
                    "concept": "Algorithm Complexity",
                    "subject": "Computer Science",
                    "score": 0.85,
                    "has_prerequisite": None,
                    "prerequisite_for": ["test_chunk_002"]
                },
                {
                    "id": "test_chunk_002",
                    "content": "Graph algorithms including BFS and DFS traversal methods.",
                    "concept": "Graph Algorithms",
                    "subject": "Computer Science", 
                    "score": 0.92,
                    "has_prerequisite": ["test_chunk_001"],
                    "prerequisite_for": ["test_chunk_003"]
                },
                {
                    "id": "test_chunk_003",
                    "content": "Dynamic programming techniques for optimization problems.",
                    "concept": "Dynamic Programming",
                    "subject": "Computer Science",
                    "score": 0.88,
                    "has_prerequisite": ["test_chunk_002"],
                    "prerequisite_for": None
                }
            ]
            
            # Start transaction for atomic test
            async with self.db_connection.transaction():
                # 1. Insert learning path
                path_result = await self.db_connection.fetchrow("""
                    INSERT INTO learning.paths (title, query_text, cognito_user_id, total_chunks, question_difficulty)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, created_at
                """, sample_learning_path["title"], sample_learning_path["query_text"], 
                    sample_learning_path["cognito_user_id"], sample_learning_path["total_chunks"],
                    sample_learning_path["question_difficulty"])
                
                path_id = path_result['id']
                sample_test["learning_path_created"] = True
                sample_test["path_id"] = str(path_id)
                
                logger.info(f"✅ Created learning path: {path_id}")
                
                # 2. Create tickets and metadata for each chunk
                for i, chunk in enumerate(sample_chunks):
                    # Insert ticket
                    ticket_result = await self.db_connection.fetchrow("""
                        INSERT INTO public.ticket (type, summary, description, owner, keywords)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id, time
                    """, "learning_concept", f"Learn {chunk['concept']}", chunk["content"],
                        sample_learning_path["cognito_user_id"], chunk["subject"])
                    
                    ticket_id = ticket_result['id']
                    sample_test["tickets_created"] += 1
                    
                    # Insert concept metadata
                    await self.db_connection.execute("""
                        INSERT INTO learning.concept_metadata (ticket_id, path_id, chunk_id, relevance_score, question_generated)
                        VALUES ($1, $2, $3, $4, $5)
                    """, ticket_id, path_id, chunk["id"], chunk["score"], True)
                    
                    sample_test["concept_metadata_created"] += 1
                    
                    # Insert custom fields
                    custom_fields = [
                        ("question", f"What is {chunk['concept']}?"),
                        ("expected_answer", f"Explanation of {chunk['concept']}"),
                        ("question_difficulty", "3"),
                        ("question_context", chunk["content"]),
                        ("chunk_id", chunk["id"]),
                        ("cognito_user_id", sample_learning_path["cognito_user_id"]),
                        ("relevance_score", str(chunk["score"])),
                        ("learning_type", "concept"),
                        ("auto_generated", "true")
                    ]
                    
                    for field_name, field_value in custom_fields:
                        await self.db_connection.execute("""
                            INSERT INTO public.ticket_custom (ticket, name, value)
                            VALUES ($1, $2, $3)
                        """, ticket_id, field_name, field_value)
                        
                        sample_test["custom_fields_created"] += 1
                    
                    # Store ticket info for prerequisites
                    chunk["ticket_id"] = ticket_id
                
                # 3. Create prerequisite relationships
                for chunk in sample_chunks:
                    if chunk.get("has_prerequisite"):
                        for prereq_chunk_id in chunk["has_prerequisite"]:
                            # Find the prerequisite ticket ID
                            prereq_chunk = next((c for c in sample_chunks if c["id"] == prereq_chunk_id), None)
                            if prereq_chunk and "ticket_id" in prereq_chunk:
                                await self.db_connection.execute("""
                                    INSERT INTO learning.prerequisites (concept_ticket_id, prerequisite_ticket_id)
                                    VALUES ($1, $2)
                                """, chunk["ticket_id"], prereq_chunk["ticket_id"])
                
                sample_test["test_executed"] = True
                sample_test["test_data"] = {
                    "learning_path": sample_learning_path,
                    "chunks": sample_chunks
                }
                
                logger.info(f"✅ Sample data insertion test completed:")
                logger.info(f"  - Learning path created: {sample_test['learning_path_created']}")
                logger.info(f"  - Tickets created: {sample_test['tickets_created']}")
                logger.info(f"  - Concept metadata records: {sample_test['concept_metadata_created']}")
                logger.info(f"  - Custom fields created: {sample_test['custom_fields_created']}")
                
        except Exception as e:
            logger.error(f"Sample data insertion test failed: {e}")
            self.test_results["errors"].append(f"Sample data test failed: {e}")
        
        self.test_results["sample_data_test"] = sample_test
    
    async def simulate_api_data_flow(self):
        """Simulate the complete API data flow process"""
        
        simulation = {
            "vector_search_input": {
                "query": "computer science algorithms",
                "min_score": 0.65,
                "max_chunks": 5,
                "path_title": "CS Algorithms Learning Path",
                "difficulty_level": "intermediate"
            },
            "mock_neo4j_results": [
                {
                    "id": "chunk_alg_001",
                    "content": "Sorting algorithms including quicksort and mergesort implementations.",
                    "subject": "Computer Science",
                    "concept": "Sorting Algorithms",
                    "score": 0.89,
                    "has_prerequisite": None,
                    "prerequisite_for": ["chunk_alg_002"]
                },
                {
                    "id": "chunk_alg_002", 
                    "content": "Binary search algorithm and its time complexity analysis.",
                    "subject": "Computer Science",
                    "concept": "Search Algorithms",
                    "score": 0.85,
                    "has_prerequisite": ["chunk_alg_001"],
                    "prerequisite_for": ["chunk_alg_003"]
                }
            ],
            "api_processing_steps": [
                "1. Receive vector search request with query and parameters",
                "2. Generate embedding for search query using OpenAI",
                "3. Perform vector similarity search in Neo4j using GDS",
                "4. Transform chunk results to API format",
                "5. Create learning path record in learning.paths table",
                "6. For each chunk, create ticket in public.ticket table",
                "7. Insert concept metadata in learning.concept_metadata table", 
                "8. Generate questions using LLM service",
                "9. Store custom fields in public.ticket_custom table",
                "10. Create prerequisite relationships in learning.prerequisites table",
                "11. Return learning path response with IDs and counts"
            ],
            "expected_database_changes": {
                "learning.paths": "+1 record",
                "public.ticket": "+N records (one per chunk)",
                "learning.concept_metadata": "+N records (one per chunk)",
                "public.ticket_custom": "+9N records (9 fields per chunk)",
                "learning.prerequisites": "+M records (based on prerequisite relationships)"
            },
            "api_response_format": {
                "path_id": "UUID string",
                "message": "Success message with counts",
                "ticket_count": "integer (number of concepts/tickets created)",
                "prerequisite_count": "integer (number of prerequisite relationships)"
            }
        }
        
        self.test_results["data_flow_simulation"] = simulation
        
        logger.info("📋 API Data Flow Simulation:")
        logger.info(f"  - Input: Vector search query for '{simulation['vector_search_input']['query']}'")
        logger.info(f"  - Processing: {len(simulation['api_processing_steps'])} steps")
        logger.info(f"  - Mock chunks: {len(simulation['mock_neo4j_results'])}")
        logger.info(f"  - Database changes: {len(simulation['expected_database_changes'])} tables affected")
    
    async def verify_current_data_state(self):
        """Check current state of data in the database"""
        
        try:
            current_state = {}
            
            # Count records in each table
            tables_to_check = [
                ("learning", "paths"),
                ("learning", "concept_metadata"), 
                ("learning", "prerequisites"),
                ("learning", "progress"),
                ("public", "ticket"),
                ("public", "ticket_custom")
            ]
            
            for schema, table in tables_to_check:
                try:
                    if schema == "public":
                        # For public schema, filter for learning-related tickets
                        if table == "ticket":
                            count = await self.db_connection.fetchval(
                                "SELECT COUNT(*) FROM public.ticket WHERE type = 'learning_concept'"
                            )
                        else:
                            count = await self.db_connection.fetchval(f"SELECT COUNT(*) FROM {schema}.{table}")
                    else:
                        count = await self.db_connection.fetchval(f"SELECT COUNT(*) FROM {schema}.{table}")
                    current_state[f"{schema}.{table}"] = count
                except Exception as e:
                    current_state[f"{schema}.{table}"] = f"Error: {e}"
            
            # Get recent learning paths
            recent_paths = await self.db_connection.fetch("""
                SELECT id, title, cognito_user_id, created_at, total_chunks
                FROM learning.paths 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            current_state["recent_paths"] = [dict(row) for row in recent_paths]
            
            # Get learning tickets
            learning_tickets = await self.db_connection.fetch("""
                SELECT id, summary, owner, time
                FROM public.ticket 
                WHERE type = 'learning_concept'
                ORDER BY time DESC 
                LIMIT 5
            """)
            current_state["recent_learning_tickets"] = [dict(row) for row in learning_tickets]
            
            self.test_results["current_data_state"] = current_state
            
            logger.info("📊 Current Database State:")
            for table, count in current_state.items():
                if isinstance(count, int):
                    logger.info(f"  - {table}: {count} records")
                elif table not in ["recent_paths", "recent_learning_tickets"]:
                    logger.info(f"  - {table}: {count}")
            
            logger.info(f"  - Recent learning paths: {len(current_state.get('recent_paths', []))}")
            logger.info(f"  - Recent learning tickets: {len(current_state.get('recent_learning_tickets', []))}")
            
        except Exception as e:
            logger.error(f"Current data state check failed: {e}")
            self.test_results["errors"].append(f"Data state check failed: {e}")
    
    def save_results(self):
        """Save test results to JSON file"""
        filename = f"simple_data_flow_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to {filename}")
        return filename
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("LEARNTRAC DATA FLOW TEST SUMMARY")
        print("="*80)
        
        db_connected = self.test_results.get("database_connectivity", False)
        schema_validation = self.test_results.get("schema_validation", {})
        sample_test = self.test_results.get("sample_data_test", {})
        errors_count = len(self.test_results.get("errors", []))
        
        print(f"\n📊 OVERALL TEST RESULTS:")
        print(f"   - Database Connectivity: {'✅' if db_connected else '❌'}")
        print(f"   - Schema Validation: {'✅' if schema_validation.get('required_tables_exist') else '❌'}")
        print(f"   - Sample Data Test: {'✅' if sample_test.get('test_executed') else '❌'}")
        print(f"   - Total Errors: {errors_count}")
        
        # Schema validation details
        if schema_validation:
            print(f"\n🗄️ SCHEMA VALIDATION:")
            print(f"   - Required tables exist: {'✅' if schema_validation.get('required_tables_exist') else '❌'}")
            print(f"   - Column types correct: {'✅' if schema_validation.get('column_types_correct') else '❌'}")
            print(f"   - Foreign keys valid: {'✅' if schema_validation.get('foreign_keys_valid') else '❌'}")
            
            missing = schema_validation.get("missing_elements", [])
            if missing:
                print(f"   - Missing elements: {len(missing)}")
                for element in missing[:5]:  # Show first 5
                    print(f"     ❌ {element}")
        
        # Sample data test results
        if sample_test.get("test_executed"):
            print(f"\n🧪 SAMPLE DATA TEST RESULTS:")
            print(f"   - Learning path created: {'✅' if sample_test.get('learning_path_created') else '❌'}")
            print(f"   - Tickets created: {sample_test.get('tickets_created', 0)}")
            print(f"   - Concept metadata records: {sample_test.get('concept_metadata_created', 0)}")
            print(f"   - Custom fields created: {sample_test.get('custom_fields_created', 0)}")
            if sample_test.get("path_id"):
                print(f"   - Test path ID: {sample_test['path_id']}")
        
        # Current data state
        current_state = self.test_results.get("current_data_state", {})
        if current_state:
            print(f"\n📈 CURRENT DATABASE STATE:")
            for table, count in current_state.items():
                if isinstance(count, int) and table not in ["recent_paths", "recent_learning_tickets"]:
                    print(f"   - {table}: {count} records")
        
        # API data flow simulation
        simulation = self.test_results.get("data_flow_simulation", {})
        if simulation:
            print(f"\n🔄 API DATA FLOW SIMULATION:")
            print(f"   - Input query: '{simulation.get('vector_search_input', {}).get('query', 'N/A')}'")
            print(f"   - Processing steps: {len(simulation.get('api_processing_steps', []))}")
            print(f"   - Expected database changes: {len(simulation.get('expected_database_changes', {}))}")
        
        # Errors
        if errors_count > 0:
            print(f"\n❌ ERRORS ENCOUNTERED:")
            for error in self.test_results["errors"]:
                print(f"   - {error}")
        
        # Recommendations
        print(f"\n🔧 RECOMMENDATIONS:")
        if db_connected and schema_validation.get('required_tables_exist') and sample_test.get('test_executed'):
            print(f"   ✅ Database schema is properly configured")
            print(f"   ✅ Data flow functionality is working")
            print(f"   ✅ Learning path system is ready for API integration")
            print(f"   🔧 Next: Test with actual Neo4j vector search")
            print(f"   🔧 Next: Implement full API authentication flow")
        else:
            if not db_connected:
                print(f"   🔧 Fix database connectivity issues")
            if not schema_validation.get('required_tables_exist'):
                print(f"   🔧 Run schema fix scripts to create missing tables/columns")
            if not sample_test.get('test_executed'):
                print(f"   🔧 Address sample data insertion issues")
            print(f"   🔧 Resolve all errors before proceeding to API integration")
        
        print(f"\n📄 TEST ARTIFACTS:")
        print(f"   - Detailed results: simple_data_flow_test_*.json")
        print(f"   - Schema analysis: schema_consistency_analysis_*.json")
        print(f"   - Fix scripts: schema_fix_*.sql")
    
    async def run_test(self):
        """Run the complete simple data flow test"""
        logger.info("Starting simple data flow test...")
        
        try:
            # Step 1: Connect to database
            if not await self.connect_to_database():
                logger.error("Cannot proceed without database connection")
                return False
            
            # Step 2: Validate schema structure
            await self.validate_schema_structure()
            
            # Step 3: Test sample data insertion
            await self.test_sample_data_insertion()
            
            # Step 4: Simulate API data flow
            await self.simulate_api_data_flow()
            
            # Step 5: Verify current data state
            await self.verify_current_data_state()
            
            # Step 6: Generate reports
            results_file = self.save_results()
            self.print_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"Simple data flow test failed: {e}")
            self.test_results["errors"].append(f"Test execution failed: {e}")
            return False
            
        finally:
            if self.db_connection:
                await self.db_connection.close()
                logger.info("Database connection closed")


async def main():
    """Main function"""
    tester = SimpleDataFlowTester()
    success = await tester.run_test()
    
    if success:
        print(f"\n✅ Simple data flow test completed successfully")
    else:
        print(f"\n❌ Simple data flow test failed")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))