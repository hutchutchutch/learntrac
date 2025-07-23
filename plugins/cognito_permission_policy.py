from trac.core import Component, implements
from trac.perm import IPermissionPolicy
import json

class CognitoPermissionPolicy(Component):
    implements(IPermissionPolicy)
    
    # Map Cognito groups to Trac permissions
    GROUP_PERMISSIONS = {
        'admins': [
            'TRAC_ADMIN',
            'TICKET_ADMIN',
            'MILESTONE_ADMIN',
            'WIKI_ADMIN',
            'PERMISSION_GRANT',
            'PERMISSION_REVOKE'
        ],
        'instructors': [
            'TICKET_CREATE',
            'TICKET_MODIFY',
            'TICKET_VIEW',
            'MILESTONE_CREATE',
            'MILESTONE_MODIFY',
            'MILESTONE_VIEW',
            'WIKI_CREATE',
            'WIKI_MODIFY',
            'WIKI_VIEW',
            'CHANGESET_VIEW',
            'TIMELINE_VIEW',
            'SEARCH_VIEW',
            'REPORT_CREATE',
            'REPORT_MODIFY',
            'REPORT_VIEW'
        ],
        'students': [
            'TICKET_CREATE',
            'TICKET_VIEW',
            'MILESTONE_VIEW',
            'WIKI_VIEW',
            'CHANGESET_VIEW',
            'TIMELINE_VIEW',
            'SEARCH_VIEW',
            'REPORT_VIEW'
        ]
    }
    
    def check_permission(self, action, username, resource, perm):
        """Check if user has permission based on Cognito groups"""
        if not hasattr(perm, 'req') or not perm.req:
            return None
        
        # Get user's Cognito groups from session
        groups_json = perm.req.session.get('cognito_groups', '[]')
        try:
            groups = json.loads(groups_json)
        except:
            groups = []
        
        # Get custom permissions from token
        perms_json = perm.req.session.get('cognito_permissions', '[]')
        try:
            custom_perms = json.loads(perms_json)
        except:
            custom_perms = []
        
        # Check if action is in custom permissions (from Lambda)
        if action in custom_perms:
            self.log.debug(f"Permission {action} granted to {username} via custom token claims")
            return True
        
        # Check if any group grants the requested permission
        for group in groups:
            if action in self.GROUP_PERMISSIONS.get(group, []):
                self.log.debug(f"Permission {action} granted to {username} via group {group}")
                return True
        
        # Let other policies decide
        return None