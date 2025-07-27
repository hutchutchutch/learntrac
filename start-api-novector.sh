#!/bin/bash
cd /app

# Install missing package
pip install email-validator >/dev/null 2>&1

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Temporarily disable vector index creation by patching the file
cat > /tmp/neo4j_patch.py << 'EOF'
# Patch to skip vector index creation
import sys
sys.path.insert(0, '/app')

# Import and patch the neo4j_client
from src.services.neo4j_client import neo4j_client
import logging

logger = logging.getLogger(__name__)

# Override the _create_indexes method
async def patched_create_indexes(self):
    """Create necessary indexes and constraints - patched to skip vector index"""
    async with self.driver.session() as session:
        # Create regular indexes only
        await session.run("CREATE INDEX IF NOT EXISTS FOR (t:Textbook) ON (t.textbook_id)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (c:Content) ON (c.content_id)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (con:Concept) ON (con.name)")
        await session.run("CREATE INDEX IF NOT EXISTS FOR (l:LearningPath) ON (l.path_id)")
        logger.info("Created basic Neo4j indexes (skipped vector index)")

# Apply the patch
neo4j_client._create_indexes = patched_create_indexes

# Now import the main app
from src.main import app

# Start uvicorn
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
EOF

# Run the patched version
python3 /tmp/neo4j_patch.py