#!/usr/bin/env python3
"""
Clear Neo4j database
"""

import asyncio
import logging
import os
from learntrac_api.src.pdf_processing.neo4j_connection_manager import Neo4jConnectionManager, ConnectionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def clear_database():
    """Clear all data from Neo4j database"""
    # Create connection config from environment
    config = ConnectionConfig(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    connection = Neo4jConnectionManager(config)
    await connection.connect()
    
    try:
        logger.info("Clearing all data from Neo4j database...")
        
        # Drop all constraints first
        result = await connection.execute_query("SHOW CONSTRAINTS")
        for constraint in result:
            constraint_name = constraint.get("name")
            if constraint_name:
                try:
                    await connection.execute_query(f"DROP CONSTRAINT {constraint_name}")
                    logger.info(f"Dropped constraint: {constraint_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop constraint {constraint_name}: {e}")
        
        # Drop all indexes
        result = await connection.execute_query("SHOW INDEXES")
        for index in result:
            index_name = index.get("name")
            if index_name:
                try:
                    await connection.execute_query(f"DROP INDEX {index_name}")
                    logger.info(f"Dropped index: {index_name}")
                except Exception as e:
                    logger.warning(f"Failed to drop index {index_name}: {e}")
        
        # Delete all nodes and relationships
        await connection.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("Deleted all nodes and relationships")
        
        # Verify database is empty
        result = await connection.execute_query("MATCH (n) RETURN count(n) as count")
        count = result[0]["count"] if result else 0
        logger.info(f"Database cleared. Remaining nodes: {count}")
        
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(clear_database())