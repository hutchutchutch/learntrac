"""Simplest possible Trac plugin"""
from trac.core import *

class HelloPlugin(Component):
    def __init__(self):
        Component.__init__(self)
        print "HelloPlugin: Initialized!"
        self.log.info("HelloPlugin: Initialized via log!")