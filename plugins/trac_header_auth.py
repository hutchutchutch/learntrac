"""Authentication plugin that reads headers from Nginx/OAuth2-proxy"""
from trac.core import *
from trac.web.api import IAuthenticator
from trac.config import Option

class HeaderAuthPlugin(Component):
    implements(IAuthenticator)
    
    user_header = Option('headerauth', 'user_header', 'X-User',
                        doc="Header containing username")
    email_header = Option('headerauth', 'email_header', 'X-Email',
                         doc="Header containing email")
    
    def authenticate(self, req):
        # Get user from headers set by oauth2-proxy
        user = req.get_header(self.user_header)
        email = req.get_header(self.email_header)
        
        if user:
            # Store additional info in session
            if email:
                req.session['email'] = email
            req.session.save()
            
            self.log.info("Authenticated user %s from headers", user)
            return user
            
        return None