"""
Bridge between modern Python 3.11 code and Trac's database schema
"""
import asyncpg
from typing import List, Dict, Optional
from datetime import datetime
import json

class TracDatabaseBridge:
    """Provides modern async interface to Trac's database"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def get_ticket_as_concept(self, ticket_id: int) -> Optional[Dict]:
        """Transform Trac ticket into learning concept"""
        async with self.db_pool.acquire() as conn:
            # Get base ticket data
            ticket = await conn.fetchrow("""
                SELECT 
                    id, type, time, changetime, component, severity,
                    priority, owner, reporter, cc, version, milestone,
                    status, resolution, summary, description, keywords
                FROM ticket
                WHERE id = $1
            """, ticket_id)
            
            if not ticket:
                return None
            
            # Get custom fields
            custom_fields = await conn.fetch("""
                SELECT name, value
                FROM ticket_custom
                WHERE ticket = $1
            """, ticket_id)
            
            # Transform to learning concept
            concept = dict(ticket)
            concept['custom_fields'] = {
                field['name']: field['value'] 
                for field in custom_fields
            }
            
            # Extract learning-specific fields
            concept['learning_difficulty'] = float(
                concept['custom_fields'].get('learning_difficulty', '2.0')
            )
            concept['mastery_threshold'] = float(
                concept['custom_fields'].get('mastery_threshold', '0.8')
            )
            concept['prerequisites'] = json.loads(
                concept['custom_fields'].get('prerequisite_concepts', '[]')
            )
            
            return concept
    
    async def update_ticket_learning_status(
        self, 
        ticket_id: int, 
        student_id: str,
        status: str,
        **kwargs
    ):
        """Update ticket with learning progress"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Update ticket status
                await conn.execute("""
                    UPDATE ticket 
                    SET status = $1, changetime = $2
                    WHERE id = $3
                """, status, int(datetime.now().timestamp()), ticket_id)
                
                # Add to ticket_change history
                await conn.execute("""
                    INSERT INTO ticket_change 
                    (ticket, time, author, field, oldvalue, newvalue)
                    VALUES ($1, $2, $3, 'status', 
                        (SELECT status FROM ticket WHERE id = $1), $4)
                """, ticket_id, int(datetime.now().timestamp()), 
                    student_id, status)
                
                # Update custom fields
                for field, value in kwargs.items():
                    await conn.execute("""
                        INSERT INTO ticket_custom (ticket, name, value)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (ticket, name) 
                        DO UPDATE SET value = EXCLUDED.value
                    """, ticket_id, field, str(value))
    
    async def get_student_tickets(
        self, 
        student_id: str,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get all tickets assigned to a student"""
        query = """
            SELECT t.*, 
                   array_agg(
                       json_build_object('name', tc.name, 'value', tc.value)
                   ) as custom_fields
            FROM ticket t
            LEFT JOIN ticket_custom tc ON t.id = tc.ticket
            WHERE t.owner = $1
        """
        
        params = [student_id]
        
        if status_filter:
            query += " AND t.status = ANY($2)"
            params.append(status_filter)
        
        query += " GROUP BY t.id"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_milestone_progress(self, milestone: str) -> Dict:
        """Get learning progress for a milestone"""
        async with self.db_pool.acquire() as conn:
            # Get all tickets in milestone
            tickets = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM ticket
                WHERE milestone = $1
                GROUP BY status
            """, milestone)
            
            total = sum(t['count'] for t in tickets)
            completed = sum(
                t['count'] for t in tickets 
                if t['status'] in ('closed', 'mastered')
            )
            
            return {
                'milestone': milestone,
                'total_concepts': total,
                'completed_concepts': completed,
                'progress_percentage': (completed / total * 100) if total > 0 else 0,
                'status_breakdown': {
                    t['status']: t['count'] for t in tickets
                }
            }
    
    async def create_learning_ticket(
        self,
        title: str,
        description: str,
        component: str = "learning",
        type: str = "task",
        custom_fields: Optional[Dict[str, str]] = None
    ) -> int:
        """Create a new learning ticket"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Insert ticket
                ticket_id = await conn.fetchval("""
                    INSERT INTO ticket 
                    (type, time, changetime, component, severity, priority,
                     owner, reporter, cc, version, milestone, status, resolution,
                     summary, description, keywords)
                    VALUES ($1, $2, $3, $4, 'normal', 'normal',
                            '', 'system', '', '', '', 'new', '',
                            $5, $6, '')
                    RETURNING id
                """, type, int(datetime.now().timestamp()), 
                    int(datetime.now().timestamp()), component, title, description)
                
                # Insert custom fields
                if custom_fields:
                    for name, value in custom_fields.items():
                        await conn.execute("""
                            INSERT INTO ticket_custom (ticket, name, value)
                            VALUES ($1, $2, $3)
                        """, ticket_id, name, value)
                
                return ticket_id