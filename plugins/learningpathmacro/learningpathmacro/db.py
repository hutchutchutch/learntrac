"""
Database schema and operations for Learning Path plugin
"""

from trac.core import Component, implements
from trac.db import Table, Column, Index, DatabaseManager
from trac.env import IEnvironmentSetupParticipant
from trac.util.datefmt import to_utimestamp, from_utimestamp


class LearningPathDB(Component):
    """Database backend for learning paths."""
    
    implements(IEnvironmentSetupParticipant)
    
    # Define database schema
    SCHEMA = [
        Table('learning_path', key='id')[
            Column('id', type='integer', auto_increment=True),
            Column('name', type='text'),
            Column('title', type='text'),
            Column('description', type='text'),
            Column('parent_id', type='integer'),
            Column('position', type='integer'),
            Column('difficulty', type='text'),  # beginner, intermediate, advanced
            Column('estimated_hours', type='integer'),
            Column('created', type='integer'),
            Column('modified', type='integer'),
            Index(['parent_id']),
            Index(['name']),
        ],
        Table('learning_path_prerequisites', key=('path_id', 'prerequisite_id'))[
            Column('path_id', type='integer'),
            Column('prerequisite_id', type='integer'),
            Column('required', type='integer'),  # 1 = required, 0 = recommended
            Index(['path_id']),
            Index(['prerequisite_id']),
        ],
        Table('learning_path_resources', key='id')[
            Column('id', type='integer', auto_increment=True),
            Column('path_id', type='integer'),
            Column('type', type='text'),  # wiki, ticket, external, video, etc.
            Column('resource_id', type='text'),
            Column('title', type='text'),
            Column('url', type='text'),
            Column('position', type='integer'),
            Index(['path_id']),
        ],
        Table('learning_path_progress', key=('username', 'path_id'))[
            Column('username', type='text'),
            Column('path_id', type='integer'),
            Column('status', type='text'),  # not_started, in_progress, completed
            Column('progress', type='integer'),  # 0-100
            Column('started', type='integer'),
            Column('completed', type='integer'),
            Column('last_accessed', type='integer'),
            Index(['username']),
            Index(['path_id']),
        ],
    ]
    
    # IEnvironmentSetupParticipant methods
    
    def environment_created(self):
        """Called when a new Trac environment is created."""
        self.upgrade_environment()
    
    def environment_needs_upgrade(self):
        """Check if the plugin needs to perform any upgrades."""
        dbm = DatabaseManager(self.env)
        return not all(dbm.has_table(table.name) for table in self.SCHEMA)
    
    def upgrade_environment(self):
        """Perform any necessary upgrades."""
        dbm = DatabaseManager(self.env)
        
        with self.env.db_transaction as db:
            # Create tables if they don't exist
            for table in self.SCHEMA:
                if not dbm.has_table(table.name):
                    for statement in dbm.to_sql(table):
                        db(statement)
                    self.log.info(f"Created table {table.name}")
            
            # Insert sample data for demonstration
            if not list(db("SELECT * FROM learning_path LIMIT 1")):
                self._insert_sample_data(db)
    
    def _insert_sample_data(self, db):
        """Insert sample learning paths for demonstration."""
        
        now = to_utimestamp(None)
        
        # Insert root learning paths
        sample_paths = [
            ('python-programming', 'Python Programming', 
             'Complete path to learn Python programming', None, 1, 'beginner', 40),
            ('web-development', 'Web Development', 
             'Modern web development with HTML, CSS, and JavaScript', None, 2, 'beginner', 60),
            ('data-science', 'Data Science', 
             'Introduction to data science and machine learning', None, 3, 'intermediate', 80),
        ]
        
        for name, title, desc, parent, pos, diff, hours in sample_paths:
            db("""INSERT INTO learning_path 
                  (name, title, description, parent_id, position, difficulty, 
                   estimated_hours, created, modified)
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
               (name, title, desc, parent, pos, diff, hours, now, now))
        
        self.log.info("Inserted sample learning paths")
    
    # Data access methods
    
    def get_learning_path(self, path_id=None, name=None):
        """Get a learning path by ID or name."""
        with self.env.db_query as db:
            if path_id:
                row = db("""SELECT id, name, title, description, parent_id, 
                           position, difficulty, estimated_hours, created, modified
                           FROM learning_path WHERE id=%s""", (path_id,))
            elif name:
                row = db("""SELECT id, name, title, description, parent_id, 
                           position, difficulty, estimated_hours, created, modified
                           FROM learning_path WHERE name=%s""", (name,))
            else:
                return None
            
            if row:
                return self._row_to_dict(row[0])
            return None
    
    def get_learning_paths(self, parent_id=None, difficulty=None):
        """Get all learning paths, optionally filtered."""
        query = """SELECT id, name, title, description, parent_id, 
                   position, difficulty, estimated_hours, created, modified
                   FROM learning_path WHERE 1=1"""
        params = []
        
        if parent_id is not None:
            query += " AND parent_id=%s"
            params.append(parent_id)
        
        if difficulty:
            query += " AND difficulty=%s"
            params.append(difficulty)
        
        query += " ORDER BY position, name"
        
        with self.env.db_query as db:
            rows = db(query, params)
            return [self._row_to_dict(row) for row in rows]
    
    def get_prerequisites(self, path_id):
        """Get prerequisites for a learning path."""
        with self.env.db_query as db:
            rows = db("""SELECT p.*, lp.name, lp.title 
                        FROM learning_path_prerequisites p
                        JOIN learning_path lp ON p.prerequisite_id = lp.id
                        WHERE p.path_id=%s
                        ORDER BY p.required DESC, lp.position""", (path_id,))
            
            return [{
                'path_id': row[0],
                'prerequisite_id': row[1],
                'required': bool(row[2]),
                'name': row[3],
                'title': row[4]
            } for row in rows]
    
    def get_resources(self, path_id):
        """Get resources for a learning path."""
        with self.env.db_query as db:
            rows = db("""SELECT id, path_id, type, resource_id, title, url, position
                        FROM learning_path_resources
                        WHERE path_id=%s
                        ORDER BY position, id""", (path_id,))
            
            return [{
                'id': row[0],
                'path_id': row[1],
                'type': row[2],
                'resource_id': row[3],
                'title': row[4],
                'url': row[5],
                'position': row[6]
            } for row in rows]
    
    def get_user_progress(self, username, path_id=None):
        """Get user progress for learning paths."""
        if path_id:
            with self.env.db_query as db:
                row = db("""SELECT username, path_id, status, progress, 
                           started, completed, last_accessed
                           FROM learning_path_progress
                           WHERE username=%s AND path_id=%s""", 
                        (username, path_id))
                if row:
                    return self._progress_row_to_dict(row[0])
                return None
        else:
            with self.env.db_query as db:
                rows = db("""SELECT username, path_id, status, progress, 
                            started, completed, last_accessed
                            FROM learning_path_progress
                            WHERE username=%s
                            ORDER BY last_accessed DESC""", (username,))
                return [self._progress_row_to_dict(row) for row in rows]
    
    def update_user_progress(self, username, path_id, progress=None, 
                           status=None, completed=False):
        """Update user progress for a learning path."""
        now = to_utimestamp(None)
        
        with self.env.db_transaction as db:
            # Check if progress record exists
            existing = db("""SELECT 1 FROM learning_path_progress 
                           WHERE username=%s AND path_id=%s""", 
                         (username, path_id))
            
            if existing:
                # Update existing record
                updates = ["last_accessed=%s"]
                params = [now]
                
                if progress is not None:
                    updates.append("progress=%s")
                    params.append(progress)
                
                if status:
                    updates.append("status=%s")
                    params.append(status)
                
                if completed:
                    updates.append("completed=%s")
                    params.append(now)
                
                params.extend([username, path_id])
                
                db(f"""UPDATE learning_path_progress 
                      SET {', '.join(updates)}
                      WHERE username=%s AND path_id=%s""", params)
            else:
                # Insert new record
                db("""INSERT INTO learning_path_progress
                      (username, path_id, status, progress, started, 
                       completed, last_accessed)
                      VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                   (username, path_id, status or 'in_progress', 
                    progress or 0, now, now if completed else None, now))
    
    def _row_to_dict(self, row):
        """Convert a database row to a dictionary."""
        return {
            'id': row[0],
            'name': row[1],
            'title': row[2],
            'description': row[3],
            'parent_id': row[4],
            'position': row[5],
            'difficulty': row[6],
            'estimated_hours': row[7],
            'created': from_utimestamp(row[8]) if row[8] else None,
            'modified': from_utimestamp(row[9]) if row[9] else None,
        }
    
    def _progress_row_to_dict(self, row):
        """Convert a progress row to a dictionary."""
        return {
            'username': row[0],
            'path_id': row[1],
            'status': row[2],
            'progress': row[3],
            'started': from_utimestamp(row[4]) if row[4] else None,
            'completed': from_utimestamp(row[5]) if row[5] else None,
            'last_accessed': from_utimestamp(row[6]) if row[6] else None,
        }