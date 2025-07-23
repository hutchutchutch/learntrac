#!/usr/bin/env python
import urllib2
import sys

try:
    # Check root URL instead of login
    response = urllib2.urlopen('http://localhost:8000/', timeout=2)
    if response.getcode() == 200:
        sys.exit(0)
except:
    pass
sys.exit(1)