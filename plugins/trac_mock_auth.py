# plugins/trac_mock_auth.py
from trac.core import *
from trac.web.api import IAuthenticator, IRequestHandler
from trac.web.chrome import INavigationContributor, add_notice
from trac.util.html import tag

class MockAuthPlugin(Component):
    implements(IAuthenticator, IRequestHandler, INavigationContributor)
    
    def authenticate(self, req):
        return req.session.get('mock_user')
    
    def match_request(self, req):
        return req.path_info.startswith('/mock-auth')
    
    def process_request(self, req):
        if req.path_info == '/mock-auth/login':
            req.session['mock_user'] = 'testuser'
            req.session.save()
            add_notice(req, "Mock login successful!")
            req.redirect(req.href.wiki())
            return None
        elif req.path_info == '/mock-auth/logout':
            req.session.clear()
            req.session.save()
            req.redirect(req.href.wiki())
            return None
        return None
    
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        if req.authname and req.authname != 'anonymous':
            yield ('metanav', 'logout', tag.a('Logout', href='/mock-auth/logout'))
        else:
            yield ('metanav', 'login', tag.a('Login', href='/mock-auth/login'))