#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test database connection and permissions for creating the learning schema.
This script verifies connectivity to the RDS PostgreSQL instance and tests
the permissions needed to create the learning schema and tables.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import argparse
from datetime import datetime
import json


class LearningDatabaseConnectionTester:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user
        }
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.conn.cursor()
            print(f"✓ Successfully connected to database at {self.host}")
            
            # Get connection info
            self.cursor.execute("SELECT current_database(), current_user, version();")
            db_info = self.cursor.fetchone()
            print(f"  Database: {db_info[0]}")
            print(f"  User: {db_info[1]}")
            print(f"  PostgreSQL Version: {db_info[2].split(',')[0]}")
            
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False
    
    def test_public_schema_access(self):
        """Test read access to Trac tables in public schema"""
        try:
            # Check if we can see the public schema
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'public'
            """)
            if not self.cursor.fetchone():
                print("✗ Cannot access public schema")
                return False
            
            print("✓ Can access public schema")
            
            # Check if we can read from ticket table
            self.cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'ticket'
            """)
            
            if self.cursor.fetchone()[0] > 0:
                print("✓ Can see ticket table in public schema")
                
                # Try to actually read from it
                try:
                    self.cursor.execute("SELECT COUNT(*) FROM public.ticket")
                    count = self.cursor.fetchone()[0]
                    print(f"✓ Can read from public.ticket table ({count} records)")
                    return True
                except Exception as e:
                    print(f"✗ Cannot read from public.ticket: {e}")
                    return False
            else:
                print("✗ Cannot see ticket table in public schema")
                return False
                
        except Exception as e:
            print(f"✗ Error testing public schema access: {e}")
            return False
    
    def test_schema_creation_permissions(self):
        """Test if we can create schemas"""
        test_schema = 'test_permissions_schema'
        
        try:
            # Try to create a test schema
            self.cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                sql.Identifier(test_schema)
            ))
            self.conn.commit()
            print(f"✓ Can create schemas (created '{test_schema}')")
            
            # Clean up
            self.cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(
                sql.Identifier(test_schema)
            ))
            self.conn.commit()
            print(f"✓ Can drop schemas (cleaned up '{test_schema}')")
            
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Cannot create schemas: {e}")
            return False
    
    def test_table_creation_permissions(self):
        """Test if we can create and drop tables"""
        try:
            # Create a temporary test table in public schema
            self.cursor.execute("""
                CREATE TEMP TABLE test_permissions_table (
                    id SERIAL PRIMARY KEY,
                    test_data TEXT
                )
            """)
            
            # Insert test data
            self.cursor.execute("""
                INSERT INTO test_permissions_table (test_data) 
                VALUES ('test')
            """)
            
            # Read it back
            self.cursor.execute("SELECT * FROM test_permissions_table")
            self.cursor.fetchone()
            
            # Table will be automatically dropped as it's TEMP
            self.conn.commit()
            print("✓ Can create, write to, and read from tables")
            
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Cannot create tables: {e}")
            return False
    
    def test_uuid_extension(self):
        """Test if UUID extension is available"""
        try:
            # Check if pgcrypto extension exists
            self.cursor.execute("""
                SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto'
            """)
            
            if self.cursor.fetchone():
                print("✓ pgcrypto extension is already installed")
            else:
                # Try to create it
                try:
                    self.cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
                    self.conn.commit()
                    print("✓ Successfully installed pgcrypto extension")
                except Exception as e:
                    self.conn.rollback()
                    print(f"✗ Cannot create pgcrypto extension: {e}")
                    print("  Note: This might require superuser privileges")
                    return False
            
            # Test UUID generation
            self.cursor.execute("SELECT gen_random_uuid()")
            uuid_result = self.cursor.fetchone()[0]
            print(f"✓ UUID generation works: {uuid_result}")
            
            return True
        except Exception as e:
            print(f"✗ Error testing UUID extension: {e}")
            return False
    
    def test_learning_schema_exists(self):
        """Check if learning schema already exists"""
        try:
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'learning'
            """)
            
            if self.cursor.fetchone():
                print("⚠ Learning schema already exists")
                
                # Check what tables exist in it
                self.cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'learning'
                    ORDER BY table_name
                """)
                
                tables = [row[0] for row in self.cursor.fetchall()]
                if tables:
                    print(f"  Existing tables: {', '.join(tables)}")
                else:
                    print("  No tables in learning schema")
                
                return True
            else:
                print("✓ Learning schema does not exist (ready to create)")
                return False
                
        except Exception as e:
            print(f"✗ Error checking learning schema: {e}")
            return None
    
    def document_connection_params(self):
        """Document the connection parameters"""
        print("\n=== Connection Parameters ===")
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Database: {self.database}")
        print(f"User: {self.user}")
        print("Password: [REDACTED]")
        
        # Save to JSON file for other scripts
        params_file = os.path.join(
            os.path.dirname(__file__), 
            'connection_params.json'
        )
        
        params_data = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'timestamp': datetime.now().isoformat(),
            'verified': True
        }
        
        try:
            with open(params_file, 'w') as f:
                json.dump(params_data, f, indent=2)
            print(f"\n✓ Connection parameters saved to: {params_file}")
        except Exception as e:
            print(f"\n✗ Could not save connection parameters: {e}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def run_all_tests(self):
        """Run all connection and permission tests"""
        print("\n=== Learning Schema Database Connection Tests ===\n")
        
        if not self.connect():
            return False
        
        tests = [
            ("Public Schema Access", self.test_public_schema_access),
            ("Schema Creation Permissions", self.test_schema_creation_permissions),
            ("Table Creation Permissions", self.test_table_creation_permissions),
            ("UUID Extension", self.test_uuid_extension),
            ("Learning Schema Status", self.test_learning_schema_exists),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            results[test_name] = test_func()
        
        # Document connection parameters
        self.document_connection_params()
        
        # Summary
        print("\n=== Test Summary ===")
        passed = sum(1 for v in results.values() if v is True)
        warnings = sum(1 for v in results.values() if v is None)
        failed = sum(1 for v in results.values() if v is False)
        total = len(results)
        
        for test_name, result in results.items():
            if result is True:
                status = "PASS"
            elif result is None:
                status = "WARN"
            else:
                status = "FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed} passed, {warnings} warnings, {failed} failed (out of {total} tests)")
        
        self.close()
        
        # Return True if all critical tests passed
        critical_tests = [
            "Public Schema Access",
            "Schema Creation Permissions",
            "Table Creation Permissions"
        ]
        
        return all(results.get(test, False) for test in critical_tests)


def main():
    parser = argparse.ArgumentParser(
        description='Test database connection and permissions for learning schema'
    )
    parser.add_argument('--host', 
                        default=os.environ.get('DB_HOST', 
                                'learntrac-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com'),
                        help='Database host')
    parser.add_argument('--port', type=int, 
                        default=int(os.environ.get('DB_PORT', 5432)),
                        help='Database port')
    parser.add_argument('--database', 
                        default=os.environ.get('DB_NAME', 'learntrac'),
                        help='Database name')
    parser.add_argument('--user', 
                        default=os.environ.get('DB_USER', 'learntrac_admin'),
                        help='Database user')
    parser.add_argument('--password', 
                        default=os.environ.get('DB_PASSWORD'),
                        help='Database password (or use DB_PASSWORD env var)')
    
    args = parser.parse_args()
    
    if not args.password:
        print("Error: Database password required.")
        print("Set DB_PASSWORD environment variable or use --password")
        sys.exit(1)
    
    tester = LearningDatabaseConnectionTester(
        args.host, args.port, args.database, 
        args.user, args.password
    )
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()