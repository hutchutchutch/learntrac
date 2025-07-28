#!/usr/bin/env python
import os
import sys
from trac.admin.console import TracAdmin
from trac.env import Environment
import shutil

trac_env_path = '/var/trac/projects'

# Create basic Trac environment
admin = TracAdmin(trac_env_path)

# For now, use SQLite to get Trac working
# We can migrate to RDS later
db_string = 'sqlite:db/trac.db'

# do_initenv expects a string with space-separated arguments
# Format: project_name db_string [repos_type repos_path]
init_args = '"LearnTrac Legacy" %s' % db_string
try:
    admin.do_initenv(init_args)
except Exception as e:
    print("Error initializing Trac: %s" % e)
    # If it already exists, that's OK
    if "already exists" not in str(e):
        raise

# Initialize with basic configuration
env = Environment(trac_env_path)

# Copy our custom config
if os.path.exists('/app/config/trac.ini'):
    shutil.copy('/app/config/trac.ini', os.path.join(trac_env_path, 'conf', 'trac.ini'))

# Set Python path to include plugins
sys.path.insert(0, '/app/plugins')

print("Trac environment initialized successfully")