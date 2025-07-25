# Trac Database Schema Initialization

This directory contains SQL scripts to initialize the Trac 1.4.4 database schema on PostgreSQL.

## Overview

The initialization process creates all necessary tables, indexes, permissions, and default data required for a fresh Trac installation.

## Files

### Trac Schema Files
- `01_trac_schema_init.sql` - Creates all Trac tables, indexes, and default enumerations
- `02_trac_permissions_init.sql` - Sets up default permissions and creates admin user
- `03_validate_schema.sql` - Validates that all tables and data were created correctly
- `initialize_trac_db.sh` - Shell script to execute all SQL files in order

### Learning Schema Files
- `04_learning_schema_init.sql` - Creates learning namespace with paths, concepts, and progress tracking
- `05_learning_schema_migrate.sql` - Handles learning schema migrations and updates
- `06_learning_schema_rollback.sql` - Removes learning schema (use with caution!)
- `07_validate_learning_schema.sql` - Validates learning schema structure and integrity
- `initialize_learning_schema.sh` - Shell script to initialize learning schema
- `LEARNING_SCHEMA_README.md` - Detailed documentation for learning schema

### Documentation
- `README.md` - This documentation file

## Prerequisites

1. PostgreSQL client tools installed (`psql` command)
2. Access to the RDS PostgreSQL instance
3. Database credentials (username and password)
4. Target database already created

## Usage

### Method 1: Using the Shell Script (Recommended)

```bash
# Set environment variables
export DB_PASSWORD="your-database-password"
export DB_HOST="hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com"
export DB_NAME="learntrac"
export DB_USER="tracadmin"

# Run the initialization script
./initialize_trac_db.sh
```

### Method 2: Manual Execution

```bash
# Connect to database and run scripts manually
psql -h hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com \
     -p 5432 -U tracadmin -d learntrac

# In psql prompt, run:
\i 01_trac_schema_init.sql
\i 02_trac_permissions_init.sql
\i 03_validate_schema.sql
```

## Schema Details

### Core Tables Created

1. **System Tables**
   - `system` - Tracks database version and configuration
   - `cache` - Application cache

2. **Ticket Management**
   - `ticket` - Main ticket table
   - `ticket_change` - Ticket history
   - `ticket_custom` - Custom ticket fields
   - `enum` - Ticket priorities, severities, types, resolutions
   - `component` - Project components
   - `milestone` - Project milestones
   - `version` - Product versions

3. **Wiki System**
   - `wiki` - Wiki pages and revisions

4. **Permission System**
   - `permission` - User permissions
   - `session` - User sessions
   - `session_attribute` - Session data
   - `auth_cookie` - Authentication cookies

5. **Repository Integration**
   - `repository` - Repository configuration
   - `revision` - Commit information
   - `node_change` - File changes

6. **Other Features**
   - `attachment` - File attachments
   - `report` - Saved queries
   - `notify_subscription` - Notification subscriptions
   - `notify_watch` - Watch list

### Default Data

1. **Enumerations**
   - Priorities: blocker, critical, major, minor, trivial
   - Resolutions: fixed, invalid, wontfix, duplicate, worksforme
   - Severities: blocker, critical, major, normal, minor, trivial, enhancement
   - Ticket Types: defect, enhancement, task

2. **Default Components**
   - component1 (example component)

3. **Default Milestones**
   - milestone1 (example milestone)

4. **Default Versions**
   - 1.0 (example version)

5. **Permissions**
   - Anonymous: Basic view permissions
   - Authenticated: Create and modify tickets/wiki
   - Admin: Full administrative access
   - Developer: Standard developer permissions

6. **Default Wiki Pages**
   - WikiStart - Welcome page
   - TracGuide - User guide

7. **Default Reports**
   - Active Tickets
   - Active Tickets by Version

## Validation

The `03_validate_schema.sql` script checks:

1. All required tables exist
2. Row counts for key tables
3. Default enumerations are present
4. Admin permissions are configured
5. Database version is set
6. Key indexes are created

Expected validation results:
- 21 tables created
- 4 enum types (priority, resolution, severity, ticket_type)
- ~35 admin permissions
- 2 default reports

## Security Notes

1. **Change Admin Password**: The default admin user has no password. Set one immediately after installation.
2. **Database Credentials**: Store database passwords securely, never commit them to version control.
3. **Network Security**: Ensure RDS security groups only allow connections from authorized sources.

## Troubleshooting

### Connection Issues
- Verify RDS endpoint is correct
- Check security group allows connections from your IP
- Ensure database exists and user has proper permissions

### Schema Creation Failures
- Check if schema already exists
- Verify user has CREATE permissions
- Review PostgreSQL logs for detailed errors

### Validation Failures
- Some counts may vary slightly based on Trac version
- Missing tables indicate incomplete initialization
- Re-run failed scripts individually to identify issues

## Integration with Trac

After successful initialization:

1. Update Trac configuration file (`trac.ini`) with database connection:
   ```ini
   [trac]
   database = postgres://tracadmin:password@hutch-learntrac-dev-db.c1uuigcm4bd1.us-east-2.rds.amazonaws.com:5432/learntrac?schema=trac
   ```

2. Start Trac application
3. Access Trac web interface
4. Log in as admin and set password
5. Configure project settings

## Learning Schema Integration

The LearnTrac system extends Trac with educational tracking capabilities through a dedicated `learning` schema. See `LEARNING_SCHEMA_README.md` for detailed information.

### Quick Setup
```bash
# After Trac schema is initialized, run:
./initialize_learning_schema.sh
```

### Key Features
- Learning paths and concept management
- Prerequisite tracking and validation
- User progress monitoring
- Integration with Trac tickets and wiki pages
- UUID-based primary keys for distributed systems
- JSONB metadata for flexibility

## Maintenance

- Regular backups recommended using `pg_dump`
- Monitor table growth, especially ticket_change, wiki, and learning.activities
- Consider partitioning for large installations
- Update statistics regularly for query performance
- Run validation scripts periodically to ensure data integrity