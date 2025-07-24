# -*- coding: utf-8 -*-
"""
TracLearn Database Bridge
Provides database compatibility layer for Python 3.11 service
"""

from __future__ import absolute_import, print_function, unicode_literals

import json
import sqlite3
from contextlib import contextmanager

try:
    # Python 2/3 compatibility
    import ConfigParser as configparser
except ImportError:
    import configparser

class DatabaseBridge(object):
    """Bridge for database access from Python 3.11 service"""
    
    def __init__(self, trac_conf_path):
        """Initialize with path to trac.ini"""
        self.config = self._load_config(trac_conf_path)
        self.db_type = self._detect_db_type()
        self.connection_params = self._get_connection_params()
    
    def _load_config(self, conf_path):
        """Load Trac configuration"""
        config = configparser.ConfigParser()
        config.read(conf_path)
        return config
    
    def _detect_db_type(self):
        """Detect database type from Trac config"""
        db_uri = self.config.get('trac', 'database', '')
        
        if db_uri.startswith('sqlite:'):
            return 'sqlite'
        elif db_uri.startswith('postgres:') or db_uri.startswith('postgresql:'):
            return 'postgresql'
        elif db_uri.startswith('mysql:'):
            return 'mysql'
        else:
            raise ValueError('Unsupported database type: %s' % db_uri)
    
    def _get_connection_params(self):
        """Extract connection parameters from Trac config"""
        db_uri = self.config.get('trac', 'database', '')
        
        if self.db_type == 'sqlite':
            # Extract path from sqlite:db/trac.db
            path = db_uri.replace('sqlite:', '')
            return {'path': path}
        
        elif self.db_type == 'postgresql':
            # Parse postgresql://user:pass@host:port/dbname
            import re
            match = re.match(
                r'postgres(?:ql)?://(?:([^:]+)(?::([^@]+))?@)?'
                r'([^:/]+)(?::(\d+))?/(.+)', db_uri)
            if match:
                user, password, host, port, dbname = match.groups()
                return {
                    'host': host or 'localhost',
                    'port': int(port) if port else 5432,
                    'user': user or 'postgres',
                    'password': password or '',
                    'database': dbname
                }
        
        elif self.db_type == 'mysql':
            # Parse mysql://user:pass@host:port/dbname
            import re
            match = re.match(
                r'mysql://(?:([^:]+)(?::([^@]+))?@)?'
                r'([^:/]+)(?::(\d+))?/(.+)', db_uri)
            if match:
                user, password, host, port, dbname = match.groups()
                return {
                    'host': host or 'localhost',
                    'port': int(port) if port else 3306,
                    'user': user or 'root',
                    'password': password or '',
                    'database': dbname
                }
        
        raise ValueError('Failed to parse database URI')
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(self.connection_params['path'])
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        
        elif self.db_type == 'postgresql':
            import psycopg2
            import psycopg2.extras
            
            conn = psycopg2.connect(
                host=self.connection_params['host'],
                port=self.connection_params['port'],
                user=self.connection_params['user'],
                password=self.connection_params['password'],
                database=self.connection_params['database']
            )
            conn.cursor_factory = psycopg2.extras.DictCursor
            try:
                yield conn
            finally:
                conn.close()
        
        elif self.db_type == 'mysql':
            import mysql.connector
            
            conn = mysql.connector.connect(
                host=self.connection_params['host'],
                port=self.connection_params['port'],
                user=self.connection_params['user'],
                password=self.connection_params['password'],
                database=self.connection_params['database']
            )
            try:
                yield conn
            finally:
                conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # For SELECT queries
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
    
    def execute_transaction(self, queries):
        """Execute multiple queries in a transaction"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                for query, params in queries:
                    cursor.execute(query, params)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise e


class TracLearnDatabaseAPI(object):
    """High-level database API for TracLearn"""
    
    def __init__(self, bridge):
        self.bridge = bridge
    
    # Course operations
    def get_courses(self, status='active'):
        """Get list of courses"""
        query = """
            SELECT id, course_code, title, description, instructor,
                   start_date, end_date, max_students, status
            FROM traclearn_courses
            WHERE status = %s
            ORDER BY start_date DESC
        """
        return self.bridge.execute_query(query, (status,))
    
    def get_course(self, course_id):
        """Get single course by ID"""
        query = """
            SELECT id, course_code, title, description, instructor,
                   start_date, end_date, max_students, status
            FROM traclearn_courses
            WHERE id = %s
        """
        results = self.bridge.execute_query(query, (course_id,))
        return results[0] if results else None
    
    def create_course(self, course_data):
        """Create new course"""
        query = """
            INSERT INTO traclearn_courses 
            (course_code, title, description, instructor,
             start_date, end_date, max_students, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            course_data['course_code'],
            course_data['title'],
            course_data.get('description', ''),
            course_data['instructor'],
            course_data.get('start_date'),
            course_data.get('end_date'),
            course_data.get('max_students', 50),
            course_data.get('status', 'active')
        )
        return self.bridge.execute_query(query, params)
    
    # Enrollment operations
    def get_enrollments(self, student_username=None, course_id=None):
        """Get enrollments with optional filters"""
        conditions = []
        params = []
        
        if student_username:
            conditions.append("e.student_username = %s")
            params.append(student_username)
        
        if course_id:
            conditions.append("e.course_id = %s")
            params.append(course_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = """
            SELECT e.id, e.course_id, e.student_username, e.enrollment_date,
                   e.status, e.grade, e.completion_date,
                   c.course_code, c.title
            FROM traclearn_enrollments e
            JOIN traclearn_courses c ON e.course_id = c.id
            %s
            ORDER BY e.enrollment_date DESC
        """ % where_clause
        
        return self.bridge.execute_query(query, params)
    
    def enroll_student(self, course_id, student_username):
        """Enroll student in course"""
        query = """
            INSERT INTO traclearn_enrollments
            (course_id, student_username, status)
            VALUES (%s, %s, 'enrolled')
        """
        return self.bridge.execute_query(query, (course_id, student_username))
    
    # Progress tracking
    def record_progress(self, enrollment_id, ticket_id, progress_type, 
                       progress_value, details=None):
        """Record learning progress"""
        query = """
            INSERT INTO traclearn_progress
            (enrollment_id, ticket_id, progress_type, progress_value, details)
            VALUES (%s, %s, %s, %s, %s)
        """
        details_json = json.dumps(details) if details else None
        params = (enrollment_id, ticket_id, progress_type, 
                 progress_value, details_json)
        return self.bridge.execute_query(query, params)
    
    def get_progress(self, enrollment_id):
        """Get progress for an enrollment"""
        query = """
            SELECT id, ticket_id, progress_type, progress_value,
                   details, recorded_at
            FROM traclearn_progress
            WHERE enrollment_id = %s
            ORDER BY recorded_at DESC
        """
        return self.bridge.execute_query(query, (enrollment_id,))
    
    # Analytics operations
    def record_analytics(self, analytics_type, entity_type, entity_id,
                        metric_name, metric_value, metadata=None):
        """Record analytics data"""
        query = """
            INSERT INTO traclearn_analytics
            (analytics_type, entity_type, entity_id, metric_name,
             metric_value, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        metadata_json = json.dumps(metadata) if metadata else None
        params = (analytics_type, entity_type, entity_id,
                 metric_name, metric_value, metadata_json)
        return self.bridge.execute_query(query, params)
    
    def get_analytics(self, entity_type, entity_id, limit=100):
        """Get analytics for an entity"""
        query = """
            SELECT analytics_type, metric_name, metric_value,
                   metadata, calculated_at
            FROM traclearn_analytics
            WHERE entity_type = %s AND entity_id = %s
            ORDER BY calculated_at DESC
            LIMIT %s
        """
        return self.bridge.execute_query(query, (entity_type, entity_id, limit))
    
    # AI insights operations
    def save_insight(self, insight_type, entity_type, entity_id,
                    insight_text, confidence_score=None, 
                    action_recommended=None):
        """Save AI-generated insight"""
        query = """
            INSERT INTO traclearn_ai_insights
            (insight_type, entity_type, entity_id, insight_text,
             confidence_score, action_recommended)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (insight_type, entity_type, entity_id, insight_text,
                 confidence_score, action_recommended)
        return self.bridge.execute_query(query, params)
    
    def get_insights(self, entity_type, entity_id, active_only=True):
        """Get AI insights for an entity"""
        query = """
            SELECT id, insight_type, insight_text, confidence_score,
                   action_recommended, generated_at, applied
            FROM traclearn_ai_insights
            WHERE entity_type = %s AND entity_id = %s
        """
        params = [entity_type, entity_id]
        
        if active_only:
            query += " AND applied = %s"
            params.append(False)
        
        query += " ORDER BY generated_at DESC"
        
        return self.bridge.execute_query(query, params)
    
    # Utility methods
    def get_enrollment_stats(self, course_id):
        """Get enrollment statistics for a course"""
        query = """
            SELECT 
                COUNT(*) as total_enrolled,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'dropped' THEN 1 ELSE 0 END) as dropped,
                AVG(CASE WHEN grade IS NOT NULL 
                    THEN CAST(SUBSTR(grade, 1, 1) AS FLOAT) ELSE NULL END) as avg_grade
            FROM traclearn_enrollments
            WHERE course_id = %s
        """
        return self.bridge.execute_query(query, (course_id,))
    
    def get_course_completion_rate(self, course_id):
        """Calculate course completion rate"""
        stats = self.get_enrollment_stats(course_id)
        if stats and stats[0]['total_enrolled'] > 0:
            return float(stats[0]['completed']) / stats[0]['total_enrolled']
        return 0.0