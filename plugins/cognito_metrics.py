from trac.core import Component
from datetime import datetime
import json

class CognitoMetrics(Component):
    """Track Cognito authentication metrics"""
    
    def __init__(self):
        super().__init__()
        self._ensure_metrics_table()
    
    def _ensure_metrics_table(self):
        """Ensure the auth_metrics table exists"""
        with self.env.db_transaction as db:
            cursor = db.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'auth_metrics'
                )
            """)
            exists = cursor.fetchone()[0]
            
            if not exists:
                cursor.execute("""
                    CREATE TABLE auth_metrics (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        event_type VARCHAR(50) NOT NULL,
                        username VARCHAR(100),
                        success BOOLEAN NOT NULL,
                        details TEXT
                    )
                """)
                cursor.execute("""
                    CREATE INDEX idx_auth_metrics_timestamp ON auth_metrics(timestamp);
                """)
                cursor.execute("""
                    CREATE INDEX idx_auth_metrics_event_type ON auth_metrics(event_type);
                """)
                cursor.execute("""
                    CREATE INDEX idx_auth_metrics_username ON auth_metrics(username);
                """)
                self.log.info("Created auth_metrics table")
    
    def record_auth_event(self, event_type, username, success, details=None):
        """Record authentication events for monitoring"""
        
        with self.env.db_transaction as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO auth_metrics 
                (timestamp, event_type, username, success, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (datetime.now(), event_type, username, success, 
                  json.dumps(details) if details else None))
        
        # Log for immediate monitoring
        if success:
            self.log.info(f"Auth success: {event_type} for {username}")
        else:
            self.log.warning(f"Auth failure: {event_type} for {username} - {details}")
    
    def get_auth_stats(self, hours=24):
        """Get authentication statistics for the last N hours"""
        from datetime import timedelta
        
        since = datetime.now() - timedelta(hours=hours)
        
        with self.env.db_query as db:
            cursor = db.cursor()
            
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failures
                FROM auth_metrics
                WHERE timestamp > %s
            """, (since,))
            
            overall = cursor.fetchone()
            
            # Stats by event type
            cursor.execute("""
                SELECT 
                    event_type,
                    COUNT(*) as count,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
                FROM auth_metrics
                WHERE timestamp > %s
                GROUP BY event_type
                ORDER BY count DESC
            """, (since,))
            
            by_type = cursor.fetchall()
            
            # Recent failures
            cursor.execute("""
                SELECT timestamp, event_type, username, details
                FROM auth_metrics
                WHERE timestamp > %s AND NOT success
                ORDER BY timestamp DESC
                LIMIT 10
            """, (since,))
            
            recent_failures = cursor.fetchall()
            
            return {
                'overall': {
                    'total': overall[0] or 0,
                    'successes': overall[1] or 0,
                    'failures': overall[2] or 0
                },
                'by_type': [
                    {
                        'event_type': row[0],
                        'count': row[1],
                        'successes': row[2]
                    }
                    for row in by_type
                ],
                'recent_failures': [
                    {
                        'timestamp': row[0].isoformat(),
                        'event_type': row[1],
                        'username': row[2],
                        'details': json.loads(row[3]) if row[3] else None
                    }
                    for row in recent_failures
                ]
            }