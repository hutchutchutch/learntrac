# lambda/api-handler-example.py

import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda handler for API Gateway requests with Cognito authorization.
    Demonstrates how to extract JWT claims and handle different HTTP methods.
    """
    
    try:
        # Log the incoming event (redact sensitive data)
        logger.info(f"Received event: {json.dumps({
            'httpMethod': event.get('httpMethod'),
            'resource': event.get('resource'),
            'path': event.get('path'),
            'headers': {k: v for k, v in event.get('headers', {}).items() if k.lower() != 'authorization'}
        })}")
        
        # Extract JWT claims from the authorizer context
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub')
        user_email = claims.get('email')
        user_groups = claims.get('custom:groups', '').split(',')
        user_permissions = claims.get('trac_permissions', '').split(',')
        
        logger.info(f"User: {user_email}, Groups: {user_groups}, Permissions: {len(user_permissions)}")
        
        # Route based on HTTP method and resource
        http_method = event.get('httpMethod')
        resource = event.get('resource')
        
        # Example routing
        if resource == '/api/v1/learning/courses' and http_method == 'GET':
            return handle_get_courses(event, claims)
        elif resource == '/api/v1/learning/courses' and http_method == 'POST':
            return handle_create_course(event, claims)
        elif resource == '/api/v1/learning/courses/{courseId}' and http_method == 'GET':
            return handle_get_course(event, claims)
        elif resource == '/api/v1/trac/tickets' and http_method == 'GET':
            return handle_get_tickets(event, claims)
        else:
            return create_response(404, {'error': 'Resource not found'})
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def handle_get_courses(event: Dict[str, Any], claims: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET /api/v1/learning/courses"""
    
    # Check permissions
    permissions = claims.get('trac_permissions', '').split(',')
    if 'LEARNING_PARTICIPATE' not in permissions and 'LEARNING_INSTRUCT' not in permissions and 'LEARNING_ADMIN' not in permissions:
        return create_response(403, {'error': 'Insufficient permissions'})
    
    # Example response - in real implementation, query from DynamoDB or RDS
    courses = [
        {
            'id': 'course-001',
            'title': 'Introduction to Trac',
            'description': 'Learn the basics of Trac project management',
            'instructor': 'admin@learntrac.com',
            'duration': '4 weeks',
            'enrolled': 45,
            'created_at': '2025-01-15T10:00:00Z'
        },
        {
            'id': 'course-002',
            'title': 'Advanced Trac Workflows',
            'description': 'Master complex Trac workflows and customizations',
            'instructor': 'instructor@learntrac.com',
            'duration': '6 weeks',
            'enrolled': 23,
            'created_at': '2025-01-20T10:00:00Z'
        }
    ]
    
    # Filter based on user role
    if 'students' in claims.get('custom:groups', '').split(','):
        # Students only see courses they're enrolled in
        user_enrollments = claims.get('custom:course_enrollments', '').split(',')
        courses = [c for c in courses if c['id'] in user_enrollments]
    
    return create_response(200, {
        'courses': courses,
        'total': len(courses)
    })

def handle_create_course(event: Dict[str, Any], claims: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /api/v1/learning/courses"""
    
    # Check permissions
    permissions = claims.get('trac_permissions', '').split(',')
    if 'COURSE_CREATE' not in permissions:
        return create_response(403, {'error': 'Insufficient permissions to create courses'})
    
    # Parse request body
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid request body'})
    
    # Validate required fields
    required_fields = ['title', 'description', 'duration']
    missing_fields = [f for f in required_fields if f not in body]
    if missing_fields:
        return create_response(400, {'error': f'Missing required fields: {", ".join(missing_fields)}'})
    
    # Create course (example)
    course = {
        'id': f'course-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'title': body['title'],
        'description': body['description'],
        'duration': body['duration'],
        'instructor': claims.get('email'),
        'created_by': claims.get('sub'),
        'created_at': datetime.now().isoformat(),
        'enrolled': 0
    }
    
    # In real implementation, save to database
    logger.info(f"Created course: {course['id']} by user: {claims.get('email')}")
    
    return create_response(201, course)

def handle_get_course(event: Dict[str, Any], claims: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET /api/v1/learning/courses/{courseId}"""
    
    course_id = event.get('pathParameters', {}).get('courseId')
    if not course_id:
        return create_response(400, {'error': 'Course ID required'})
    
    # Example course detail
    course = {
        'id': course_id,
        'title': 'Introduction to Trac',
        'description': 'Learn the basics of Trac project management',
        'instructor': {
            'name': 'John Doe',
            'email': 'instructor@learntrac.com'
        },
        'duration': '4 weeks',
        'modules': [
            {
                'id': 'module-001',
                'title': 'Getting Started with Trac',
                'duration': '1 week',
                'lessons': 5
            },
            {
                'id': 'module-002',
                'title': 'Ticket Management',
                'duration': '1 week',
                'lessons': 7
            }
        ],
        'enrolled': 45,
        'created_at': '2025-01-15T10:00:00Z'
    }
    
    # Check if user has access
    user_enrollments = claims.get('custom:course_enrollments', '').split(',')
    permissions = claims.get('trac_permissions', '').split(',')
    
    if course_id not in user_enrollments and 'LEARNING_ADMIN' not in permissions and 'LEARNING_INSTRUCT' not in permissions:
        return create_response(403, {'error': 'Not enrolled in this course'})
    
    return create_response(200, course)

def handle_get_tickets(event: Dict[str, Any], claims: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET /api/v1/trac/tickets"""
    
    # Check Trac permissions
    permissions = claims.get('trac_permissions', '').split(',')
    if 'TICKET_VIEW' not in permissions:
        return create_response(403, {'error': 'Insufficient permissions to view tickets'})
    
    # Example tickets - in real implementation, query from Trac database
    tickets = [
        {
            'id': 123,
            'summary': 'Fix login issue in course enrollment',
            'status': 'open',
            'priority': 'high',
            'owner': claims.get('email') if 'TICKET_MODIFY' in permissions else None,
            'created': '2025-01-20T10:00:00Z'
        }
    ]
    
    return create_response(200, {
        'tickets': tickets,
        'total': len(tickets)
    })

def create_response(status_code: int, body: Dict[str, Any], headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Create API Gateway Lambda response"""
    
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps(body)
    }
    
    if headers:
        response['headers'].update(headers)
    
    return response