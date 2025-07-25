#!/usr/bin/env python3
"""
Trac Database Connection and Basic Operations Test
Tests database connectivity and performs basic Trac operations
"""

import os
import sys
import psycopg2
from datetime import datetime
import argparse

class TracDatabaseTester:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                options='-c search_path=trac,public'
            )
            self.cursor = self.conn.cursor()
            print(f"✓ Successfully connected to database at {self.host}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False
    
    def test_schema_exists(self):
        """Check if Trac schema exists"""
        try:
            self.cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'trac'
            """)
            result = self.cursor.fetchone()
            if result:
                print("✓ Trac schema exists")
                return True
            else:
                print("✗ Trac schema not found")
                return False
        except Exception as e:
            print(f"✗ Error checking schema: {e}")
            return False
    
    def test_tables_exist(self):
        """Check if required tables exist"""
        required_tables = [
            'system', 'ticket', 'wiki', 'permission', 'session',
            'component', 'milestone', 'version', 'enum'
        ]
        
        try:
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'trac'
            """)
            existing_tables = [row[0] for row in self.cursor.fetchall()]
            
            all_exist = True
            for table in required_tables:
                if table in existing_tables:
                    print(f"✓ Table '{table}' exists")
                else:
                    print(f"✗ Table '{table}' missing")
                    all_exist = False
            
            return all_exist
        except Exception as e:
            print(f"✗ Error checking tables: {e}")
            return False
    
    def test_database_version(self):
        """Check database version"""
        try:
            self.cursor.execute("""
                SELECT value FROM system WHERE name = 'database_version'
            """)
            result = self.cursor.fetchone()
            if result:
                print(f"✓ Database version: {result[0]}")
                return True
            else:
                print("✗ Database version not found")
                return False
        except Exception as e:
            print(f"✗ Error checking database version: {e}")
            return False
    
    def test_create_ticket(self):
        """Test creating a ticket"""
        try:
            # Get next ticket ID
            self.cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM ticket")
            ticket_id = self.cursor.fetchone()[0]
            
            # Create test ticket
            self.cursor.execute("""
                INSERT INTO ticket (
                    id, type, time, changetime, component, severity,
                    priority, owner, reporter, status, resolution,
                    summary, description
                ) VALUES (
                    %s, 'task', %s, %s, 'component1', 'normal',
                    'major', 'admin', 'test_user', 'new', NULL,
                    'Test ticket from database validation',
                    'This is a test ticket created during database validation.'
                )
            """, (
                ticket_id,
                int(datetime.now().timestamp() * 1000000),
                int(datetime.now().timestamp() * 1000000)
            ))
            
            self.conn.commit()
            print(f"✓ Successfully created test ticket #{ticket_id}")
            return ticket_id
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error creating ticket: {e}")
            return None
    
    def test_permissions(self):
        """Check if admin permissions exist"""
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM permission WHERE username = 'admin'
            """)
            count = self.cursor.fetchone()[0]
            if count > 0:
                print(f"✓ Admin has {count} permissions")
                return True
            else:
                print("✗ No admin permissions found")
                return False
        except Exception as e:
            print(f"✗ Error checking permissions: {e}")
            return False
    
    def test_enumerations(self):
        """Check if default enumerations exist"""
        try:
            self.cursor.execute("""
                SELECT type, COUNT(*) as count 
                FROM enum 
                GROUP BY type 
                ORDER BY type
            """)
            results = self.cursor.fetchall()
            
            expected_types = ['priority', 'resolution', 'severity', 'ticket_type']
            found_types = [row[0] for row in results]
            
            all_exist = True
            for etype in expected_types:
                if etype in found_types:
                    count = next(row[1] for row in results if row[0] == etype)
                    print(f"✓ Enumeration '{etype}' has {count} values")
                else:
                    print(f"✗ Enumeration '{etype}' missing")
                    all_exist = False
            
            return all_exist
        except Exception as e:
            print(f"✗ Error checking enumerations: {e}")
            return False
    
    def cleanup_test_data(self, ticket_id):
        """Remove test ticket"""
        if ticket_id:
            try:
                self.cursor.execute("DELETE FROM ticket WHERE id = %s", (ticket_id,))
                self.conn.commit()
                print(f"✓ Cleaned up test ticket #{ticket_id}")
            except Exception as e:
                self.conn.rollback()
                print(f"✗ Error cleaning up test data: {e}")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def run_all_tests(self):
        """Run all validation tests"""
        print("\n=== Trac Database Validation Tests ===\n")
        
        if not self.connect():
            return False
        
        tests = [
            ("Schema Exists", self.test_schema_exists),
            ("Tables Exist", self.test_tables_exist),
            ("Database Version", self.test_database_version),
            ("Permissions", self.test_permissions),
            ("Enumerations", self.test_enumerations),
            ("Create Ticket", self.test_create_ticket)
        ]
        
        results = {}
        ticket_id = None
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            if test_name == "Create Ticket":
                result = test_func()
                ticket_id = result
                results[test_name] = result is not None
            else:
                results[test_name] = test_func()
        
        # Cleanup
        if ticket_id:
            print("\n--- Cleanup ---")
            self.cleanup_test_data(ticket_id)
        
        # Summary
        print("\n=== Test Summary ===")
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        self.close()
        return passed == total


def main():
    parser = argparse.ArgumentParser(description='Test Trac database connection and schema')
    parser.add_argument('--host', default='hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com',
                        help='Database host')
    parser.add_argument('--port', type=int, default=5432,
                        help='Database port')
    parser.add_argument('--database', default='learntrac',
                        help='Database name')
    parser.add_argument('--user', default='tracadmin',
                        help='Database user')
    parser.add_argument('--password', default=os.environ.get('DB_PASSWORD'),
                        help='Database password (or use DB_PASSWORD env var)')
    
    args = parser.parse_args()
    
    if not args.password:
        print("Error: Database password required. Set DB_PASSWORD environment variable or use --password")
        sys.exit(1)
    
    tester = TracDatabaseTester(
        args.host, args.port, args.database, 
        args.user, args.password
    )
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()