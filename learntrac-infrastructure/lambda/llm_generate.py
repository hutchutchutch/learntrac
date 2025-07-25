"""
Lambda function for generating learning questions using OpenAI
"""
import json
import os
import boto3
import logging
from typing import Dict, Any, List
import time

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager')

# Cache for API key
_api_key_cache = None
_cache_timestamp = 0
CACHE_TTL = 300  # 5 minutes

def get_openai_api_key() -> str:
    """Retrieve OpenAI API key from Secrets Manager with caching"""
    global _api_key_cache, _cache_timestamp
    
    current_time = time.time()
    if _api_key_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _api_key_cache
    
    secret_name = os.environ.get('OPENAI_API_KEY_SECRET')
    if not secret_name:
        raise ValueError("OPENAI_API_KEY_SECRET environment variable not set")
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        _api_key_cache = response['SecretString']
        _cache_timestamp = current_time
        return _api_key_cache
    except Exception as e:
        logger.error(f"Failed to retrieve API key: {e}")
        raise

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating learning questions
    
    Expected input:
    {
        "content": "The content to generate questions from",
        "difficulty": "1-5",
        "count": 3,
        "context": "optional context"
    }
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        content = body.get('content', '').strip()
        difficulty = int(body.get('difficulty', 3))
        count = int(body.get('count', 3))
        context = body.get('context', '')
        
        # Validate inputs
        if not content:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Content is required'})
            }
        
        if not 1 <= difficulty <= 5:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Difficulty must be between 1 and 5'})
            }
        
        # Get API key
        api_key = get_openai_api_key()
        
        # Import OpenAI (from Lambda layer)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Create prompt
        difficulty_map = {
            1: "very basic/beginner",
            2: "beginner",
            3: "intermediate",
            4: "advanced",
            5: "expert"
        }
        
        prompt = f"""Generate {count} learning questions based on the following content.
        
Content: {content}

Difficulty Level: {difficulty_map[difficulty]}
{f'Additional Context: {context}' if context else ''}

Requirements:
1. Questions should test understanding, not just memorization
2. Include a mix of conceptual and practical questions
3. Questions should be clear and unambiguous
4. Provide the expected answer for each question

Format your response as JSON array with objects containing:
- question: The question text
- expected_answer: The ideal answer
- hints: Optional hints to guide the learner

Example format:
[
    {{
        "question": "What is...",
        "expected_answer": "The answer is...",
        "hints": ["Think about...", "Consider..."]
    }}
]"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model=os.environ.get('MODEL_NAME', 'gpt-4'),
            messages=[
                {"role": "system", "content": "You are an expert educator creating learning assessment questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=float(os.environ.get('TEMPERATURE', '0.7')),
            max_tokens=int(os.environ.get('MAX_TOKENS', '1000')),
            response_format={"type": "json_object"}
        )
        
        # Parse response
        questions_json = response.choices[0].message.content
        questions = json.loads(questions_json)
        
        # Ensure we have a list
        if isinstance(questions, dict) and 'questions' in questions:
            questions = questions['questions']
        elif not isinstance(questions, list):
            questions = [questions]
        
        # Log metrics
        logger.info(f"Generated {len(questions)} questions for difficulty {difficulty}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'questions': questions,
                'count': len(questions),
                'difficulty': difficulty,
                'model': os.environ.get('MODEL_NAME', 'gpt-4')
            })
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }