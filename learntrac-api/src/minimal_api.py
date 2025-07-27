import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
import redis
import json
from datetime import datetime
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="LearnTrac API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize connections
neo4j_driver = None
redis_client = None

# Import auth router
from routers.auth import router as auth_router

# Include auth router
app.include_router(auth_router)

@app.on_event("startup")
async def startup():
    global neo4j_driver, redis_client
    logger.info("Starting LearnTrac API...")
    
    # Connect to Neo4j
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if neo4j_uri and neo4j_user and neo4j_password:
        try:
            neo4j_driver = GraphDatabase.driver(
                neo4j_uri, 
                auth=(neo4j_user, neo4j_password)
            )
            neo4j_driver.verify_connectivity()
            print(f"✓ Connected to Neo4j at {neo4j_uri}")
        except Exception as e:
            print(f"✗ Neo4j connection failed: {e}")
    
    # Connect to Redis
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            redis_client = redis.from_url(redis_url)
            redis_client.ping()
            print("✓ Connected to Redis")
        except Exception as e:
            print(f"✗ Redis connection failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    if neo4j_driver:
        neo4j_driver.close()

@app.get("/")
async def root():
    """Root endpoint for API status"""
    return {
        "status": "ok", 
        "service": "LearnTrac API",
        "endpoints": {
            "auth": "/auth/*",
            "api": "/api/trac/*",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "learning-api"}

@app.get("/api/trac/textbooks")
async def get_textbooks(subject: str = None, limit: int = 20, offset: int = 0):
    """Get textbooks from Neo4j"""
    
    if not neo4j_driver:
        # Return mock data if Neo4j is not connected
        mock_textbooks = [
            {
                "textbook_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Introduction to Computer Science",
                "subject": "Computer Science",
                "authors": ["John Doe", "Jane Smith"],
                "pages_processed": 450,
                "chunks_created": 1823,
                "created_at": "2024-01-15T10:30:00Z"
            },
            {
                "textbook_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Advanced Mathematics",
                "subject": "Mathematics",
                "authors": ["Alice Johnson"],
                "pages_processed": 320,
                "chunks_created": 1290,
                "created_at": "2024-01-14T15:45:00Z"
            }
        ]
        
        if subject:
            mock_textbooks = [t for t in mock_textbooks if t["subject"] == subject]
        
        return {"textbooks": mock_textbooks[offset:offset+limit]}
    
    # Query Neo4j
    try:
        with neo4j_driver.session() as session:
            query = """
            MATCH (t:Textbook)
            WHERE $subject IS NULL OR t.subject = $subject
            RETURN t
            ORDER BY t.created_at DESC
            SKIP $offset LIMIT $limit
            """
            
            result = session.run(query, subject=subject, offset=offset, limit=limit)
            
            textbooks = []
            for record in result:
                textbook = dict(record["t"])
                textbooks.append(textbook)
            
            return {"textbooks": textbooks}
    except Exception as e:
        print(f"Neo4j query failed: {e}")
        # Return empty list if query fails
        return {"textbooks": []}

@app.post("/api/trac/textbooks/upload")
async def upload_textbook():
    """Mock textbook upload"""
    return {
        "textbook_id": f"text-{datetime.now().timestamp()}",
        "title": "Uploaded Textbook",
        "pages_processed": 200,
        "chunks_created": 800,
        "concepts_extracted": 150,
        "processing_time": 45.2,
        "status": "completed"
    }

@app.get("/api/trac/neo4j/status")
async def neo4j_status():
    """Check Neo4j connection status"""
    if not neo4j_driver:
        return {"connected": False, "error": "No driver configured"}
    
    try:
        neo4j_driver.verify_connectivity()
        
        # Get some stats
        with neo4j_driver.session() as session:
            # Get counts separately since UNION requires same column names
            stats = {}
            
            result = session.run("MATCH (t:Textbook) RETURN count(t) as count")
            stats["textbooks"] = result.single()["count"]
            
            result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            stats["chunks"] = result.single()["count"]
            
            result = session.run("MATCH (n:Concept) RETURN count(n) as count")
            stats["concepts"] = result.single()["count"]
        
        return {
            "connected": True, 
            "uri": os.getenv("NEO4J_URI"),
            "stats": stats
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)