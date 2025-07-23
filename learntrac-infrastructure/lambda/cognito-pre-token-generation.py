# lambda/cognito-pre-token-generation.py

import json

def handler(event, context):
    """
    Pre-token generation Lambda trigger for Cognito.
    This function customizes the JWT tokens before they are generated.
    """
    
    # Log the incoming event for debugging
    print(f"Event: {json.dumps(event)}")
    
    # Get the user's groups from the event
    groups = event['request'].get('groupConfiguration', {}).get('groupsToOverride', [])
    
    # Map Cognito groups to Trac permissions
    permission_map = {
        'admins': [
            'TRAC_ADMIN',
            'TICKET_ADMIN', 
            'WIKI_ADMIN',
            'MILESTONE_ADMIN',
            'LEARNING_ADMIN'
        ],
        'instructors': [
            'TICKET_CREATE',
            'TICKET_MODIFY',
            'WIKI_CREATE',
            'WIKI_MODIFY',
            'LEARNING_INSTRUCT',
            'LEARNING_MENTOR'
        ],
        'students': [
            'TICKET_VIEW',
            'WIKI_VIEW',
            'TICKET_CREATE',
            'LEARNING_PARTICIPATE',
            'LEARNING_PRACTICE'
        ]
    }
    
    # Collect all permissions for user's groups
    permissions = []
    for group in groups:
        if group in permission_map:
            permissions.extend(permission_map[group])
    
    # Remove duplicates
    permissions = list(set(permissions))
    
    # Add custom claims to both ID and Access tokens
    event['response']['claimsOverrideDetails'] = {
        'claimsToAddOrOverride': {
            'trac_permissions': ','.join(permissions),
            'custom:groups': ','.join(groups),
            'custom:permission_count': str(len(permissions))
        }
    }
    
    # Log what we're adding
    print(f"Adding permissions: {permissions}")
    print(f"For groups: {groups}")
    
    return event