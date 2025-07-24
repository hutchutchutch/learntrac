# -*- coding: utf-8 -*-
"""
TracLearn - Educational Learning Management Plugin for Trac
A bridge between Python 2.7 (Trac) and Python 3.11 (Modern AI/Analytics)

This plugin provides learning management features integrated with Trac's
ticket system, including analytics, AI-powered insights, and voice interfaces.
"""

from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
from pkg_resources import resource_filename

from trac.core import Component, implements
from trac.env import IEnvironmentSetupParticipant
from trac.db import DatabaseManager
from trac.util.translation import _

# Version information
__version__ = '0.1.0'
__author__ = 'TracLearn Team'
__author_email__ = 'traclearn@example.com'
__url__ = 'https://github.com/example/traclearn'

class TracLearnSetup(Component):
    """Main setup component for TracLearn plugin"""
    
    implements(IEnvironmentSetupParticipant)
    
    # IEnvironmentSetupParticipant methods
    
    def environment_created(self):
        """Called when a new Trac environment is created"""
        self._create_tables()
        self._set_default_config()
        self.log.info("TracLearn plugin initialized for new environment")
    
    def environment_needs_upgrade(self, db=None):
        """Check if the environment needs an upgrade"""
        if db is None:
            with self.env.db_query as db:
                return self._check_upgrade_needed(db)
        else:
            return self._check_upgrade_needed(db)
    
    def upgrade_environment(self, db=None):
        """Upgrade the environment database schema"""
        if db is None:
            with self.env.db_transaction as db:
                self._upgrade_db(db)
        else:
            self._upgrade_db(db)
        
        self.log.info("TracLearn database schema upgraded")
    
    # Private methods
    
    def _create_tables(self):
        """Create TracLearn database tables"""
        db_backend = DatabaseManager(self.env).get_database_type()
        
        # Import appropriate schema based on database type
        if db_backend == 'postgres':
            from traclearn.db.schema import postgres_schema as schema
        elif db_backend == 'mysql':
            from traclearn.db.schema import mysql_schema as schema
        else:
            from traclearn.db.schema import sqlite_schema as schema
        
        with self.env.db_transaction as db:
            cursor = db.cursor()
            for table_sql in schema:
                cursor.execute(table_sql)
            
            # Create version tracking entry
            cursor.execute("""
                INSERT INTO system (name, value) 
                VALUES ('traclearn_version', %s)
            """, (str(__version__),))
    
    def _check_upgrade_needed(self, db):
        """Check if database upgrade is needed"""
        cursor = db.cursor()
        
        # Check if TracLearn tables exist
        try:
            cursor.execute("SELECT value FROM system WHERE name='traclearn_version'")
            row = cursor.fetchone()
            if row:
                current_version = row[0]
                return current_version != __version__
            else:
                return True
        except:
            return True
    
    def _upgrade_db(self, db):
        """Perform database upgrades"""
        from traclearn.db.upgrades import upgrade_manager
        upgrade_manager.upgrade(self.env, db)
    
    def _set_default_config(self):
        """Set default configuration values"""
        config = self.config
        
        # TracLearn section
        if 'traclearn' not in config:
            config.add_section('traclearn')
        
        defaults = {
            'api_enabled': 'true',
            'api_port': '8000',
            'analytics_enabled': 'true',
            'ai_features_enabled': 'true',
            'voice_interface_enabled': 'false',
            'default_language': 'en',
            'max_file_size': '10485760',  # 10MB
            'cache_ttl': '3600',  # 1 hour
            'python3_executable': sys.executable or 'python3',
            'api_base_url': 'http://localhost:8000/api/v1',
        }
        
        for key, value in defaults.items():
            if not config.get('traclearn', key):
                config.set('traclearn', key, value)
        
        # Components section - enable TracLearn components
        components_to_enable = [
            'traclearn.components.learning_manager.LearningManager',
            'traclearn.components.analytics_collector.AnalyticsCollector',
            'traclearn.components.ai_integration.AIIntegration',
            'traclearn.web.handlers.TracLearnHandler',
            'traclearn.ticket_extensions.learning_fields.LearningFieldsProvider',
        ]
        
        for component in components_to_enable:
            config.set('components', component, 'enabled')
        
        config.save()

# Component loading helper
def load_components():
    """Load all TracLearn components"""
    # This will be called by Trac's component system
    from traclearn.components import learning_manager
    from traclearn.components import analytics_collector
    from traclearn.components import ai_integration
    from traclearn.web import handlers
    from traclearn.ticket_extensions import learning_fields

# Export main components
__all__ = ['TracLearnSetup', '__version__', 'load_components']