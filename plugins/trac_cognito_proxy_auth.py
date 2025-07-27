"""
Cognito Authentication Plugin for Trac
Uses the learntrac-api container as a proxy for JWT validation
"""

from trac.core import *
from trac.web.api import IAuthenticator, IRequestFilter, IRequestHandler, HTTPNotFound
from trac.web.chrome import INavigationContributor, add_notice, add_warning
from trac.util.translation import _
from trac.util.html import tag
import json
import urllib2
import urllib
import traceback

class CognitoProxyAuthPlugin(Component):
    """Cognito authentication using learntrac-api as JWT validation proxy"""
    
    implements(IAuthenticator, IRequestFilter, IRequestHandler, INavigationContributor)
    
    def __init__(self):
        Component.__init__(self)
        self.log.info("=== CognitoProxyAuthPlugin INITIALIZING ===")
        
        self.region = self.config.get('cognito', 'region', 'us-east-2')
        self.user_pool_id = self.config.get('cognito', 'user_pool_id', 'us-east-2_1AzmDXp0K')
        self.client_id = self.config.get('cognito', 'client_id', '38r71epsido0doobd9370mqd8u')
        self.cognito_domain = self.config.get('cognito', 'domain', 'hutch-learntrac-dev-auth')
        # API endpoint for validation
        self.api_endpoint = self.config.get('learntrac', 'api_endpoint', 'http://learntrac-api:8001/api/trac')
        
        self.log.info("Cognito Config:")
        self.log.info("  Region: %s", self.region)
        self.log.info("  User Pool: %s", self.user_pool_id)
        self.log.info("  Client ID: %s", self.client_id)
        self.log.info("  Domain: %s", self.cognito_domain)
        self.log.info("  API Endpoint: %s", self.api_endpoint)
        self.log.info("=== CognitoProxyAuthPlugin INITIALIZED ===")
        
        # Track initialization state
        self._initialized = True
    
    # IAuthenticator methods
    def authenticate(self, req):
        """Extract user from session"""
        try:
            self.log.debug("=== AUTHENTICATE called ===")
            self.log.debug("Request path: %s", getattr(req, 'path_info', 'unknown'))
            self.log.debug("Session keys: %s", list(req.session.keys()) if hasattr(req, 'session') else 'no session')
            
            # Check for Cognito user in session
            cognito_user = req.session.get('cognito_username')
            
            if cognito_user:
                self.log.info("Found cognito_username in session: %s", cognito_user)
                req.authname = cognito_user
                
                # Store user data for the macro
                if req.session.get('cognito_email'):
                    auth_data = {
                        'username': cognito_user,
                        'email': req.session.get('cognito_email'),
                        'name': req.session.get('cognito_name', cognito_user),
                        'groups': req.session.get('cognito_groups', [])
                    }
                    req.session['auth_data'] = json.dumps(auth_data)
                    self.log.debug("Stored auth_data in session")
                
                return cognito_user
            else:
                self.log.debug("No cognito_username in session")
            
            return None
            
        except Exception as e:
            self.log.error("Error in authenticate: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())
            return None
    
    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        """Check if user needs to authenticate"""
        try:
            self.log.debug("=== PRE_PROCESS_REQUEST called ===")
            self.log.debug("Path: %s, Handler: %s", req.path_info, handler)
            self.log.debug("Current authname: %s", getattr(req, 'authname', 'None'))
            
            # Protected paths that require authentication
            protected_paths = ['/wiki/LearnTrac']
            
            for path in protected_paths:
                if req.path_info.startswith(path) and not req.authname:
                    self.log.info("Protected path %s requires auth, redirecting to login", path)
                    # Store the original URL to redirect back after login
                    req.session['login_redirect'] = req.path_info
                    req.redirect(req.href('/auth/login'))
            
            return handler
            
        except Exception as e:
            self.log.error("Error in pre_process_request: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())
            # Return handler to allow request to continue
            return handler
    
    def post_process_request(self, req, template, data, metadata):
        try:
            self.log.debug("=== POST_PROCESS_REQUEST called ===")
            self.log.debug("Template: %s", template)
            return template, data, metadata
        except Exception as e:
            self.log.error("Error in post_process_request: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())
            return template, data, metadata
    
    # IRequestHandler methods
    def match_request(self, req):
        """Handle Cognito auth URLs"""
        try:
            self.log.debug("=== MATCH_REQUEST called ===")
            self.log.debug("Path: %s", req.path_info)
            
            matches = req.path_info in ('/auth/login', '/auth/callback', '/auth/logout')
            self.log.debug("Matches auth URLs: %s", matches)
            
            return matches
        except Exception as e:
            self.log.error("Error in match_request: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())
            return False
    
    def process_request(self, req):
        """Process authentication requests"""
        try:
            self.log.info("=== PROCESS_REQUEST called ===")
            self.log.info("Processing path: %s", req.path_info)
            
            # Default result in case something goes wrong
            result = None
            
            if req.path_info == '/auth/login':
                # Build Cognito hosted UI URL
                base_url = "https://%s.auth.%s.amazoncognito.com" % (self.cognito_domain, self.region)
                redirect_uri = req.abs_href('/auth/callback')
                
                auth_url = "%s/login?client_id=%s&response_type=code&scope=email+openid+profile&redirect_uri=%s" % (
                    base_url, self.client_id, urllib.quote_plus(redirect_uri))
                
                self.log.info("Redirecting to Cognito: %s" % auth_url)
                req.redirect(auth_url)
                # Return empty tuple to signal request is handled
                return None
            
            elif req.path_info == '/auth/callback':
                # Handle OAuth callback
                self.log.info("Processing OAuth callback")
                code = req.args.get('code')
                error = req.args.get('error')
                
                self.log.debug("Callback params - code: %s, error: %s", 
                             'present' if code else 'none', error)
                
                if error:
                    self.log.warning("OAuth error received: %s", error)
                    add_warning(req, "Authentication failed: %s" % error)
                    req.redirect(req.href.wiki())
                    return None
                    
                if code:
                    try:
                        # Send code to API for validation
                        validation_url = "%s/auth/validate-code" % self.api_endpoint
                        redirect_uri = req.abs_href('/auth/callback')
                        
                        self.log.info("Validating code with API: %s", validation_url)
                        
                        data = json.dumps({
                            'code': code,
                            'redirect_uri': redirect_uri
                        })
                        
                        self.log.debug("Validation request data: %s", data)
                        
                        request = urllib2.Request(validation_url, data=data,
                                                headers={'Content-Type': 'application/json'})
                        
                        self.log.info("Sending validation request...")
                        response = urllib2.urlopen(request)
                        response_data = response.read()
                        self.log.debug("API response: %s", response_data)
                        
                        result = json.loads(response_data)
                        
                        if result.get('success'):
                            user_info = result.get('user_info', {})
                            self.log.info("Validation successful for user: %s", user_info.get('username'))
                            
                            # Store in session
                            req.session['cognito_username'] = user_info.get('username')
                            req.session['cognito_groups'] = user_info.get('groups', [])
                            req.session['cognito_email'] = user_info.get('email')
                            req.session['cognito_name'] = user_info.get('name', '')
                            req.session['authenticated'] = True
                            req.session.save()
                            
                            self.log.info("Session updated for user %s" % user_info.get('username'))
                            add_notice(req, "Welcome, %s!" % user_info.get('name', user_info.get('username')))
                            
                            # Redirect to original page or wiki
                            redirect_url = req.session.pop('login_redirect', req.href.wiki('LearnTrac'))
                            self.log.info("Redirecting to: %s", redirect_url)
                            req.redirect(redirect_url)
                        else:
                            error_msg = result.get('error', 'Authentication failed')
                            self.log.error("Validation failed: %s", error_msg)
                            raise Exception(error_msg)
                            
                    except Exception as e:
                        self.log.error("Authentication failed: %s" % str(e))
                        self.log.error("Traceback: %s", traceback.format_exc())
                        add_warning(req, "Authentication failed. Please try again.")
                        req.redirect(req.href.wiki())
                        return None
                
                # If no code or error, redirect to wiki
                self.log.warning("OAuth callback with no code or error")
                req.redirect(req.href.wiki())
                return None
            
            elif req.path_info == '/auth/logout':
                # Clear session
                self.log.info("Processing logout request")
                req.session.clear()
                req.session.save()
                
                # Build logout URL
                logout_uri = req.abs_href.wiki()
                logout_url = "https://%s.auth.%s.amazoncognito.com/logout?client_id=%s&logout_uri=%s" % (
                    self.cognito_domain, self.region, self.client_id, urllib.quote_plus(logout_uri))
                
                self.log.info("Logging out user, redirecting to: %s" % logout_url)
                req.redirect(logout_url)
                # Return None to signal request is handled
                return None
                
            # If we get here without returning, return a 404
            self.log.warning("No handler matched in process_request for path: %s", req.path_info)
            raise HTTPNotFound("No handler for path: %s" % req.path_info)
                
        except Exception as e:
            self.log.error("Error in process_request: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())
            # Don't try to send response in exception handler
            # Trac will handle the error
            raise

    
    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return None
    
    def get_navigation_items(self, req):
        """Add login/logout links"""
        try:
            self.log.debug("=== GET_NAVIGATION_ITEMS called ===")
            self.log.debug("Current authname: %s", getattr(req, 'authname', 'None'))
            
            if req.authname and req.authname != 'anonymous':
                self.log.debug("Adding logout link for user: %s", req.authname)
                yield ('metanav', 'logout', 
                       tag.a('Logout (%s)' % req.authname, href=req.href('/auth/logout')))
            else:
                self.log.debug("Adding login link")
                yield ('metanav', 'login', 
                       tag.a('Login', href=req.href('/auth/login')))
                       
        except Exception as e:
            self.log.error("Error in get_navigation_items: %s", str(e))
            self.log.error("Traceback: %s", traceback.format_exc())


# Import tag for HTML generation
from trac.util.html import tag