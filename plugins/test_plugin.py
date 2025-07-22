from trac.core import Component, implements
from trac.web.api import IRequestFilter
import logging

class TestPlugin(Component):
    implements(IRequestFilter)
    
    def __init__(self):
        self.log.info("========= TEST PLUGIN LOADED =========")
        super().__init__()
    
    def pre_process_request(self, req, handler):
        self.log.info(f"Test plugin processing: {req.path_info}")
        return handler
    
    def post_process_request(self, req, template, data, metadata):
        self.log.info("Test plugin post-processing")
        return template, data, metadata
