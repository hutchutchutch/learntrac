"""
Ticket Creation Service with Prerequisites
Creates Trac tickets from learning chunks with metadata and prerequisite relationships
"""

import asyncpg
import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from ..db.database import db_manager
from .llm_service import llm_service

logger = logging.getLogger(__name__)


@dataclass
class ChunkData:
    """Structured chunk data for validation"""
    id: str
    content: str
    concept: str
    subject: str
    score: float
    has_prerequisite: Optional[List[str]] = None
    prerequisite_for: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class TicketCreationError(Exception):
    """Custom exception for ticket creation failures"""
    pass


class TicketCreationService:
    """Service for creating Trac tickets from learning chunks with prerequisites"""
    
    def __init__(self):
        """Initialize the service"""
        self.db_pool = None
    
    async def initialize(self):
        """Initialize database connection"""
        if db_manager.pool:
            self.db_pool = db_manager.pool
            logger.info("Ticket creation service initialized")
        else:
            logger.error("Database pool not available")
            raise TicketCreationError("Database connection not available")
    
    def _validate_input(self, user_id: str, query: str, chunks: List[Dict]) -> List[ChunkData]:
        """
        Validate and sanitize input parameters
        
        Args:
            user_id: Cognito user ID
            query: Learning query text
            chunks: List of chunk dictionaries
            
        Returns:
            List of validated ChunkData objects
            
        Raises:
            TicketCreationError: If validation fails
        """
        # Validate user_id
        if not user_id or not isinstance(user_id, str) or len(user_id.strip()) == 0:
            raise TicketCreationError("user_id must be a non-empty string")
        
        # Validate query
        if not query or not isinstance(query, str) or len(query.strip()) == 0:
            raise TicketCreationError("query must be a non-empty string")
        
        if len(query) > 1000:
            raise TicketCreationError("query must be less than 1000 characters")
        
        # Validate chunks
        if not chunks or not isinstance(chunks, list) or len(chunks) == 0:
            raise TicketCreationError("chunks must be a non-empty list")
        
        validated_chunks = []
        required_fields = {'id', 'content', 'concept', 'subject', 'score'}
        
        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, dict):
                raise TicketCreationError(f"Chunk {i} must be a dictionary")
            
            # Check required fields
            missing_fields = required_fields - set(chunk.keys())
            if missing_fields:
                raise TicketCreationError(f"Chunk {i} missing required fields: {missing_fields}")
            
            # Validate field types and values
            if not chunk['id'] or not isinstance(chunk['id'], str):
                raise TicketCreationError(f"Chunk {i} 'id' must be a non-empty string")
            
            if not chunk['content'] or not isinstance(chunk['content'], str):
                raise TicketCreationError(f"Chunk {i} 'content' must be a non-empty string")
            
            if not chunk['concept'] or not isinstance(chunk['concept'], str):
                raise TicketCreationError(f"Chunk {i} 'concept' must be a non-empty string")
            
            if not chunk['subject'] or not isinstance(chunk['subject'], str):
                raise TicketCreationError(f"Chunk {i} 'subject' must be a non-empty string")
            
            if not isinstance(chunk['score'], (int, float)) or chunk['score'] < 0:
                raise TicketCreationError(f"Chunk {i} 'score' must be a non-negative number")
            
            # Create validated chunk data
            validated_chunk = ChunkData(
                id=chunk['id'].strip(),
                content=chunk['content'].strip(),
                concept=chunk['concept'].strip(),
                subject=chunk['subject'].strip(),
                score=float(chunk['score']),
                has_prerequisite=chunk.get('has_prerequisite'),
                prerequisite_for=chunk.get('prerequisite_for'),
                metadata=chunk.get('metadata', {})
            )
            
            validated_chunks.append(validated_chunk)
        
        return validated_chunks
    
    async def create_learning_path(
        self, 
        user_id: str, 
        query: str, 
        chunks: List[Dict],
        path_title: Optional[str] = None,
        difficulty_level: str = "intermediate"
    ) -> uuid.UUID:
        """
        Create a complete learning path with tickets and prerequisites
        
        Args:
            user_id: Cognito user ID
            query: Learning query text
            chunks: List of chunk dictionaries
            path_title: Optional custom title for the learning path
            difficulty_level: Difficulty level (beginner, intermediate, advanced)
            
        Returns:
            UUID of the created learning path
            
        Raises:
            TicketCreationError: If creation fails
        """
        if not self.db_pool:
            raise TicketCreationError("Service not initialized")
        
        # Validate input
        validated_chunks = self._validate_input(user_id, query, chunks)
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Create learning path
                    path_title = path_title or f"Learning Path: {query[:50]}..."
                    path_id = await conn.fetchval("""
                        INSERT INTO learning.learning_paths 
                        (title, description, difficulty_level, created_by, tags)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING path_id
                    """, path_title, query, difficulty_level, user_id, 
                        ["generated", "auto-created"])
                    
                    logger.info(f"Created learning path {path_id} for user {user_id}")
                    
                    # Generate tickets and questions concurrently
                    ticket_tasks = []
                    for chunk in validated_chunks:
                        task = self._create_ticket_with_question(
                            conn, chunk, user_id, query, path_id
                        )
                        ticket_tasks.append(task)
                    
                    # Execute all ticket creation tasks concurrently
                    ticket_results = await asyncio.gather(*ticket_tasks, return_exceptions=True)
                    
                    # Process results and build ticket map
                    ticket_map = {}
                    concept_metadata_list = []
                    
                    for i, result in enumerate(ticket_results):
                        if isinstance(result, Exception):
                            logger.error(f"Failed to create ticket for chunk {validated_chunks[i].id}: {result}")
                            raise TicketCreationError(f"Failed to create ticket for chunk {validated_chunks[i].id}")
                        
                        ticket_id, concept_id = result
                        chunk = validated_chunks[i]
                        ticket_map[chunk.concept] = (ticket_id, concept_id)
                        
                        # Prepare concept metadata
                        concept_metadata_list.append({
                            'concept_id': concept_id,
                            'ticket_id': ticket_id,
                            'path_id': path_id,
                            'sequence_order': i + 1,
                            'chunk_id': chunk.id,
                            'relevance_score': chunk.score
                        })
                    
                    # Store concept metadata in batch
                    await self._store_concept_metadata_batch(conn, concept_metadata_list)
                    
                    # Create prerequisite relationships
                    await self._create_prerequisite_relationships(
                        conn, validated_chunks, ticket_map
                    )
                    
                    logger.info(f"Successfully created learning path {path_id} with {len(validated_chunks)} tickets")
                    return path_id
                    
                except Exception as e:
                    logger.error(f"Error creating learning path: {e}")
                    if isinstance(e, TicketCreationError):
                        raise
                    raise TicketCreationError(f"Failed to create learning path: {str(e)}")
    
    async def _create_ticket_with_question(
        self, 
        conn: asyncpg.Connection, 
        chunk: ChunkData, 
        user_id: str, 
        query: str,
        path_id: uuid.UUID
    ) -> Tuple[int, uuid.UUID]:
        """
        Create a Trac ticket with generated question for a chunk
        
        Returns:
            Tuple of (ticket_id, concept_id)
        """
        # Generate question using LLM service
        question_data = await llm_service.generate_question(
            chunk_content=chunk.content,
            concept=chunk.concept,
            difficulty=3,
            context=query,
            question_type="comprehension"
        )
        
        if question_data.get('error'):
            logger.warning(f"LLM question generation failed for chunk {chunk.id}: {question_data['error']}")
            # Use fallback question
            question_data = {
                'question': f"What is the key concept in {chunk.concept}?",
                'expected_answer': f"The key concept involves understanding {chunk.concept} as described in the learning material."
            }
        
        # Create Trac ticket
        current_time = int(time.time())
        ticket_id = await conn.fetchval("""
            INSERT INTO ticket 
            (type, time, changetime, milestone, status, resolution, 
             summary, description, owner, reporter, keywords)
            VALUES ('learning_concept', $1, $1, $2, 'new', '', $3, $4, $5, 'learning-system', $6)
            RETURNING id
        """, current_time, chunk.subject, chunk.concept, chunk.content, 
            user_id, f"learning,{chunk.subject},{chunk.concept}")
        
        # Store custom fields
        custom_fields = [
            (ticket_id, 'question', question_data.get('question', '')),
            (ticket_id, 'expected_answer', question_data.get('expected_answer', '')),
            (ticket_id, 'question_difficulty', '3'),
            (ticket_id, 'question_context', query),
            (ticket_id, 'chunk_id', chunk.id),
            (ticket_id, 'cognito_user_id', user_id),
            (ticket_id, 'relevance_score', str(chunk.score)),
            (ticket_id, 'learning_type', 'concept'),
            (ticket_id, 'auto_generated', 'true')
        ]
        
        # Add metadata as custom fields
        if chunk.metadata:
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    custom_fields.append((ticket_id, f"metadata_{key}", str(value)))
        
        await conn.executemany("""
            INSERT INTO ticket_custom (ticket, name, value) 
            VALUES ($1, $2, $3)
        """, custom_fields)
        
        # Create concept metadata record
        concept_id = uuid.uuid4()
        
        logger.info(f"Created ticket {ticket_id} for concept '{chunk.concept}' with concept_id {concept_id}")
        return ticket_id, concept_id
    
    async def _store_concept_metadata_batch(
        self, 
        conn: asyncpg.Connection, 
        metadata_list: List[Dict]
    ):
        """Store concept metadata records in batch"""
        if not metadata_list:
            return
        
        # Prepare batch insert data
        batch_data = []
        for metadata in metadata_list:
            batch_data.append((
                metadata['concept_id'],
                metadata['ticket_id'],
                metadata['path_id'],
                metadata['sequence_order'],
                'lesson',  # concept_type
                3,  # difficulty_score
                0.8,  # mastery_threshold
                None,  # practice_questions (will be populated later)
                None,  # learning_objectives
                {'chunk_id': metadata['chunk_id'], 'relevance_score': metadata['relevance_score']},  # resources
                30,  # estimated_minutes
                ['auto-generated']  # tags
            ))
        
        await conn.executemany("""
            INSERT INTO learning.concept_metadata
            (concept_id, ticket_id, path_id, sequence_order, concept_type,
             difficulty_score, mastery_threshold, practice_questions, 
             learning_objectives, resources, estimated_minutes, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """, batch_data)
        
        logger.info(f"Stored {len(batch_data)} concept metadata records")
    
    async def _create_prerequisite_relationships(
        self, 
        conn: asyncpg.Connection, 
        chunks: List[ChunkData], 
        ticket_map: Dict[str, Tuple[int, uuid.UUID]]
    ):
        """Create prerequisite relationships between concepts"""
        prerequisite_data = []
        
        for chunk in chunks:
            if not chunk.has_prerequisite:
                continue
            
            if chunk.concept not in ticket_map:
                logger.warning(f"Cannot create prerequisites for unknown concept: {chunk.concept}")
                continue
            
            concept_ticket_id, concept_id = ticket_map[chunk.concept]
            
            # Handle both single prerequisite and list of prerequisites
            prerequisites = chunk.has_prerequisite
            if isinstance(prerequisites, str):
                prerequisites = [prerequisites]
            
            for prereq_concept in prerequisites:
                if prereq_concept in ticket_map:
                    prereq_ticket_id, prereq_concept_id = ticket_map[prereq_concept]
                    prerequisite_data.append((
                        uuid.uuid4(),  # prerequisite_id
                        concept_id,    # concept_id
                        prereq_concept_id,  # prereq_concept_id
                        'mandatory'    # requirement_type
                    ))
                    logger.info(f"Created prerequisite: {prereq_concept} -> {chunk.concept}")
                else:
                    logger.warning(f"Prerequisite concept '{prereq_concept}' not found for '{chunk.concept}'")
        
        if prerequisite_data:
            await conn.executemany("""
                INSERT INTO learning.prerequisites
                (prerequisite_id, concept_id, prereq_concept_id, requirement_type)
                VALUES ($1, $2, $3, $4)
            """, prerequisite_data)
            logger.info(f"Created {len(prerequisite_data)} prerequisite relationships")
    
    async def get_learning_path_tickets(self, path_id: uuid.UUID, user_id: str) -> List[Dict]:
        """
        Get all tickets for a learning path with their metadata
        
        Args:
            path_id: Learning path UUID
            user_id: User ID for permission checking
            
        Returns:
            List of ticket dictionaries with metadata
        """
        if not self.db_pool:
            raise TicketCreationError("Service not initialized")
        
        async with self.db_pool.acquire() as conn:
            # Get tickets with concept metadata
            rows = await conn.fetch("""
                SELECT 
                    t.id as ticket_id,
                    t.summary,
                    t.description,
                    t.status,
                    t.milestone,
                    t.created_at,
                    cm.concept_id,
                    cm.sequence_order,
                    cm.concept_type,
                    cm.difficulty_score,
                    cm.mastery_threshold,
                    cm.estimated_minutes,
                    cm.tags,
                    cm.resources,
                    -- Custom fields
                    json_object_agg(
                        tc.name, tc.value
                    ) FILTER (WHERE tc.name IS NOT NULL) as custom_fields,
                    -- Prerequisites
                    array_agg(
                        DISTINCT prereq_cm.concept_id
                    ) FILTER (WHERE prereq_cm.concept_id IS NOT NULL) as prerequisite_concepts
                FROM learning.concept_metadata cm
                JOIN ticket t ON cm.ticket_id = t.id
                LEFT JOIN ticket_custom tc ON t.id = tc.ticket
                LEFT JOIN learning.prerequisites p ON cm.concept_id = p.concept_id
                LEFT JOIN learning.concept_metadata prereq_cm ON p.prereq_concept_id = prereq_cm.concept_id
                WHERE cm.path_id = $1
                GROUP BY 
                    t.id, t.summary, t.description, t.status, t.milestone, t.created_at,
                    cm.concept_id, cm.sequence_order, cm.concept_type, 
                    cm.difficulty_score, cm.mastery_threshold, cm.estimated_minutes,
                    cm.tags, cm.resources
                ORDER BY cm.sequence_order
            """, path_id)
            
            return [dict(row) for row in rows]
    
    async def update_ticket_progress(
        self, 
        ticket_id: int, 
        user_id: str, 
        status: str,
        mastery_score: Optional[float] = None,
        time_spent_minutes: Optional[int] = None,
        notes: Optional[str] = None
    ):
        """
        Update ticket progress for a user
        
        Args:
            ticket_id: Trac ticket ID
            user_id: Student user ID
            status: New status (not_started, in_progress, completed, mastered)
            mastery_score: Optional mastery score (0.0-1.0)
            time_spent_minutes: Optional time spent in minutes
            notes: Optional progress notes
        """
        if not self.db_pool:
            raise TicketCreationError("Service not initialized")
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Get concept_id from ticket
                concept_id = await conn.fetchval("""
                    SELECT concept_id 
                    FROM learning.concept_metadata 
                    WHERE ticket_id = $1
                """, ticket_id)
                
                if not concept_id:
                    raise TicketCreationError(f"No concept found for ticket {ticket_id}")
                
                # Update or insert progress record
                current_time = datetime.utcnow()
                completed_at = current_time if status in ('completed', 'mastered') else None
                
                await conn.execute("""
                    INSERT INTO learning.progress
                    (student_id, concept_id, ticket_id, status, mastery_score,
                     time_spent_minutes, last_accessed, completed_at, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (student_id, concept_id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        mastery_score = COALESCE(EXCLUDED.mastery_score, progress.mastery_score),
                        time_spent_minutes = COALESCE(EXCLUDED.time_spent_minutes, progress.time_spent_minutes),
                        last_accessed = EXCLUDED.last_accessed,
                        completed_at = EXCLUDED.completed_at,
                        notes = COALESCE(EXCLUDED.notes, progress.notes),
                        updated_at = NOW(),
                        attempt_count = progress.attempt_count + 1
                """, user_id, concept_id, ticket_id, status, mastery_score,
                    time_spent_minutes, current_time, completed_at, notes)
                
                # Update Trac ticket status if progressed
                if status in ('completed', 'mastered'):
                    trac_status = 'closed' if status == 'mastered' else 'accepted'
                    await conn.execute("""
                        UPDATE ticket 
                        SET status = $1, changetime = $2
                        WHERE id = $3
                    """, trac_status, int(current_time.timestamp()), ticket_id)
                    
                    # Add change record
                    await conn.execute("""
                        INSERT INTO ticket_change 
                        (ticket, time, author, field, oldvalue, newvalue)
                        VALUES ($1, $2, $3, 'status', 
                            (SELECT status FROM ticket WHERE id = $1), $4)
                    """, ticket_id, int(current_time.timestamp()), user_id, trac_status)
                
                logger.info(f"Updated progress for ticket {ticket_id}, user {user_id}, status {status}")
    
    async def close(self):
        """Close any resources"""
        # Database pool is managed by db_manager
        logger.info("Ticket creation service closed")


# Create singleton instance
ticket_service = TicketCreationService()