"""
Lambda function for evaluating student answers using OpenAI
"""
import json
import os
import boto3
import logging
from typing import Dict, Any
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
    Lambda handler for evaluating student answers
    
    Expected input:
    {
        "question": "The question that was asked",
        "expected_answer": "The expected/ideal answer",
        "student_answer": "The student's answer",
        "context": "optional additional context"
    }
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '').strip()
        expected_answer = body.get('expected_answer', '').strip()
        student_answer = body.get('student_answer', '').strip()
        context = body.get('context', '')
        
        # Validate inputs
        if not all([question, expected_answer, student_answer]):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Question, expected_answer, and student_answer are required'})
            }
        
        # Get API key
        api_key = get_openai_api_key()
        
        # Import OpenAI (from Lambda layer)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Create evaluation prompt
        prompt = f"""Evaluate the student's answer to the following question.

Question: {question}

Expected Answer: {expected_answer}

Student's Answer: {student_answer}

{f'Additional Context: {context}' if context else ''}

Please evaluate the student's answer and provide:
1. A score from 0.0 to 1.0 (where 1.0 is perfect)
2. Whether the answer demonstrates mastery (score >= 0.8)
3. Constructive feedback explaining what was good and what could be improved
4. Specific suggestions for improvement if the score is below 0.8

Consider:
- Accuracy of information
- Completeness of the answer
- Understanding of key concepts
- Clarity of explanation

Format your response as JSON with:
- score: float between 0.0 and 1.0
- mastery_achieved: boolean
- feedback: string with constructive feedback
- strengths: array of strengths in the answer
- improvements: array of suggested improvements
"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model=os.environ.get('MODEL_NAME', 'gpt-4'),
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert educator evaluating student answers. Be encouraging but honest in your assessments."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=float(os.environ.get('TEMPERATURE', '0.3')),  # Lower temperature for consistency
            max_tokens=int(os.environ.get('MAX_TOKENS', '800')),
            response_format={"type": "json_object"}
        )
        
        # Parse response
        evaluation = json.loads(response.choices[0].message.content)
        
        # Ensure required fields
        if 'score' not in evaluation:
            evaluation['score'] = 0.5
        if 'mastery_achieved' not in evaluation:
            evaluation['mastery_achieved'] = evaluation['score'] >= 0.8
        if 'feedback' not in evaluation:
            evaluation['feedback'] = "Please review the expected answer and try again."
        
        # Ensure score is in valid range
        evaluation['score'] = max(0.0, min(1.0, float(evaluation['score'])))
        
        # Log metrics
        logger.info(f"Evaluated answer with score: {evaluation['score']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'evaluation': evaluation,
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
        logger.error(f"Error evaluating answer: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }