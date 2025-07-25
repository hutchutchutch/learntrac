# lambda/cognito-pre-token-generation-enhanced.py

import json
import logging
from datetime import datetime, timezone

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Enhanced Pre-token generation Lambda trigger for Cognito.
    This function customizes JWT tokens with additional claims for LearnTrac.
    """
    
    try:
        # Log the incoming event (redact sensitive data)
        safe_event = {
            'userPoolId': event.get('userPoolId'),
            'triggerSource': event.get('triggerSource'),
            'userName': event.get('userName'),
            'region': event.get('region')
        }
        logger.info(f"Pre-token generation triggered: {json.dumps(safe_event)}")
        
        # Extract user attributes and groups
        user_attributes = event['request'].get('userAttributes', {})
        groups = event['request'].get('groupConfiguration', {}).get('groupsToOverride', [])
        
        # Enhanced permission mapping with learning-specific permissions
        permission_map = {
            'admins': [
                # Trac permissions
                'TRAC_ADMIN',
                'TICKET_ADMIN', 
                'WIKI_ADMIN',
                'MILESTONE_ADMIN',
                'BROWSER_VIEW',
                'CHANGESET_VIEW',
                # Learning permissions
                'LEARNING_ADMIN',
                'COURSE_CREATE',
                'COURSE_DELETE',
                'ANALYTICS_VIEW',
                'USER_MANAGE',
                'CONTENT_MANAGE'
            ],
            'instructors': [
                # Trac permissions
                'TICKET_CREATE',
                'TICKET_MODIFY',
                'WIKI_CREATE',
                'WIKI_MODIFY',
                'MILESTONE_VIEW',
                'BROWSER_VIEW',
                # Learning permissions
                'LEARNING_INSTRUCT',
                'LEARNING_MENTOR',
                'COURSE_CREATE',
                'COURSE_MODIFY',
                'ASSIGNMENT_CREATE',
                'ASSIGNMENT_GRADE',
                'STUDENT_PROGRESS_VIEW',
                'CONTENT_CREATE'
            ],
            'students': [
                # Trac permissions
                'TICKET_VIEW',
                'WIKI_VIEW',
                'TICKET_CREATE',
                'MILESTONE_VIEW',
                'BROWSER_VIEW',
                # Learning permissions
                'LEARNING_PARTICIPATE',
                'LEARNING_PRACTICE',
                'ASSIGNMENT_SUBMIT',
                'PROGRESS_VIEW_OWN',
                'COURSE_ENROLL',
                'CONTENT_VIEW'
            ]
        }
        
        # Collect all permissions for user's groups
        permissions = []
        primary_role = 'student'  # Default role
        
        for group in groups:
            if group in permission_map:
                permissions.extend(permission_map[group])
                # Set primary role based on group precedence
                if group == 'admins':
                    primary_role = 'admin'
                elif group == 'instructors' and primary_role != 'admin':
                    primary_role = 'instructor'
        
        # Remove duplicates while preserving order
        seen = set()
        unique_permissions = []
        for perm in permissions:
            if perm not in seen:
                seen.add(perm)
                unique_permissions.append(perm)
        
        # Get user's custom attributes
        course_enrollments = user_attributes.get('custom:course_enrollments', '')
        learning_preferences = user_attributes.get('custom:learning_preferences', '')
        
        # Generate session ID for tracking
        session_id = f"{event['userName']}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Add custom claims to both ID and Access tokens
        custom_claims = {
            # Trac integration claims
            'trac_permissions': ','.join(unique_permissions),
            'trac_username': event['userName'],
            
            # Group and role claims
            'custom:groups': ','.join(groups),
            'custom:primary_role': primary_role,
            'custom:permission_count': str(len(unique_permissions)),
            
            # Learning-specific claims
            'custom:course_enrollments': course_enrollments,
            'custom:learning_preferences': learning_preferences,
            
            # Session tracking
            'custom:session_id': session_id,
            'custom:token_generated_at': datetime.now(timezone.utc).isoformat(),
            
            # Feature flags (can be used for gradual feature rollout)
            'custom:features': json.dumps({
                'ai_assistant': primary_role in ['admin', 'instructor'],
                'advanced_analytics': primary_role == 'admin',
                'peer_learning': True,
                'gamification': True
            })
        }
        
        # Apply claims to the response
        event['response']['claimsOverrideDetails'] = {
            'claimsToAddOrOverride': custom_claims,
            # Optionally suppress groups from the token to reduce size
            'groupOverrideDetails': {
                'groupsToOverride': groups,
                'iamRolesToOverride': [],
                'preferredRole': None
            }
        }
        
        # Log successful processing
        logger.info(f"Successfully processed token for user: {event['userName']}, role: {primary_role}, permissions: {len(unique_permissions)}")
        
        return event
        
    except Exception as e:
        logger.error(f"Error processing pre-token generation: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
        # Re-raise to prevent token generation on error
        raise e