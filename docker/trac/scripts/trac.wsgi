#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Trac WSGI script for gunicorn

import os
import sys

# Add plugins to path
sys.path.insert(0, '/app/plugins')

# Trac environment path
os.environ['TRAC_ENV'] = '/var/trac/projects'

# Import Trac's WSGI handler
from trac.web.main import dispatch_request

# Create the WSGI application
def application(environ, start_response):
    environ['trac.env_path'] = '/var/trac/projects'
    return dispatch_request(environ, start_response)