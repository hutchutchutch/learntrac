"""
LLM Integration Service for Question Generation
Implements API Gateway integration pattern for LLM-based question generation
"""

import aiohttp
import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..config import settings
# Redis removed - from .redis_client import redis_cache

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating questions using LLM API via API Gateway"""
    
    def __init__(self):
        self.api_gateway_url = os.getenv('API_GATEWAY_URL', 'https://api.openai.com/v1')
        self.api_key = os.getenv('LLM_API_KEY', settings.openai_api_key)
        self.timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = None
        self.circuit_breaker = CircuitBreaker()
        self.retry_config = {
            'max_retries': 3,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'exponential_base': 2.0
        }
    
    async def initialize(self):
        """Initialize the LLM service"""
        if not self.api_key:
            logger.warning("LLM API key not configured, question generation will be disabled")
            return
        
        # Create persistent session
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'LearnTrac-API/1.0'
            }
        )
        
        logger.info("LLM service initialized")
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
    
    async def generate_question(
        self, 
        chunk_content: str, 
        concept: str, 
        difficulty: int = 3, 
        context: str = "",
        question_type: str = "comprehension"
    ) -> Dict[str, Any]:
        """
        Generate a question based on chunk content
        
        Args:
            chunk_content: The learning content to generate a question from
            concept: The specific concept being tested
            difficulty: Difficulty level (1-5 scale)
            context: Additional learning context
            question_type: Type of question (comprehension, application, analysis)
            
        Returns:
            Dict containing question, expected_answer, and metadata
        """
        if not self.session or not self.api_key:
            logger.error("LLM service not properly initialized")
            return {
                'error': 'LLM service not available',
                'question': None,
                'expected_answer': None
            }
        
        # Redis removed - skip cache check
        # cache_key = self._generate_cache_key(chunk_content, concept, difficulty, context, question_type)
        # cached_result = await redis_cache.get_json(cache_key)
        # if cached_result:
        #     logger.info(f"Returning cached question for concept: {concept}")
        #     return cached_result
        
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning("Circuit breaker is open, skipping LLM call")
            return {
                'error': 'Service temporarily unavailable',
                'question': None,
                'expected_answer': None
            }
        
        try:
            # Generate prompt
            prompt = self._create_prompt(chunk_content, concept, difficulty, context, question_type)
            
            # Make API call with retry logic
            result = await self._make_llm_request(prompt)
            
            if result.get('error'):
                self.circuit_breaker.record_failure()
                return result
            
            # Parse and validate response
            parsed_result = self._parse_response(result, concept, difficulty)
            
            # Validate question quality
            if self._validate_question_quality(parsed_result):
                # Redis removed - skip caching
                # await redis_cache.set_json(cache_key, parsed_result, ttl=3600)  # 1 hour
                self.circuit_breaker.record_success()
                
                logger.info(f"Successfully generated question for concept: {concept}")
                return parsed_result
            else:
                logger.warning(f"Generated question failed quality validation for concept: {concept}")
                return {
                    'error': 'Generated question did not meet quality standards',
                    'question': None,
                    'expected_answer': None
                }
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Error generating question: {e}")
            return {
                'error': f'Question generation failed: {str(e)}',
                'question': None,
                'expected_answer': None
            }
    
    def _create_prompt(
        self, 
        chunk_content: str, 
        concept: str, 
        difficulty: int, 
        context: str,
        question_type: str
    ) -> str:
        """Create a sophisticated prompt for question generation"""
        
        # Difficulty level mapping
        difficulty_descriptions = {
            1: "Very Easy - Basic recall and recognition",
            2: "Easy - Simple understanding and identification", 
            3: "Medium - Application of concepts to familiar situations",
            4: "Hard - Analysis and synthesis of multiple concepts",
            5: "Very Hard - Evaluation and creation of new solutions"
        }
        
        # Question type templates
        question_templates = {
            "comprehension": "Create a question that tests understanding of the core concept.",
            "application": "Create a question that requires applying the concept to solve a problem.",
            "analysis": "Create a question that requires breaking down the concept into components.",
            "synthesis": "Create a question that requires combining this concept with others.",
            "evaluation": "Create a question that requires judging or critiquing the concept."
        }
        
        difficulty_desc = difficulty_descriptions.get(difficulty, difficulty_descriptions[3])
        question_template = question_templates.get(question_type, question_templates["comprehension"])
        
        prompt = f"""You are an expert educator creating assessment questions for online learning.

TASK: {question_template}

CONTENT TO ANALYZE:
{chunk_content}

TARGET CONCEPT: {concept}
DIFFICULTY LEVEL: {difficulty}/5 - {difficulty_desc}
LEARNING CONTEXT: {context if context else "General learning assessment"}

REQUIREMENTS:
1. Create ONE clear, well-formed question (100-500 characters)
2. Provide ONE comprehensive expected answer (200-1000 characters)
3. Ensure the question directly relates to the concept: "{concept}"
4. Match the difficulty level: {difficulty}/5
5. The question should be answerable based on the provided content

FORMAT YOUR RESPONSE EXACTLY AS:
QUESTION: [Your question here]
EXPECTED_ANSWER: [Your expected answer here]

QUALITY CRITERIA:
- Question is clear and unambiguous
- Question tests the specific concept mentioned
- Answer is complete and educational
- Appropriate difficulty for level {difficulty}/5
- No formatting artifacts or incomplete thoughts"""

        return prompt
    
    async def _make_llm_request(self, prompt: str) -> Dict[str, Any]:
        """Make request to LLM API with retry logic"""
        
        payload = {
            'model': 'gpt-4',
            'messages': [
                {
                    'role': 'system', 
                    'content': 'You are an expert educator creating learning assessment questions. Always follow the exact format requested.'
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Determine endpoint based on API Gateway URL
        if 'openai.com' in self.api_gateway_url:
            endpoint = f'{self.api_gateway_url}/chat/completions'
        else:
            endpoint = f'{self.api_gateway_url}/api/v1/llm/generate'
        
        for attempt in range(self.retry_config['max_retries'] + 1):
            try:
                async with self.session.post(endpoint, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    elif response.status == 429:  # Rate limit
                        wait_time = min(
                            self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt),
                            self.retry_config['max_delay']
                        )
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status in [500, 502, 503, 504]:  # Server errors
                        if attempt < self.retry_config['max_retries']:
                            wait_time = self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt)
                            logger.warning(f"Server error {response.status}, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    # For other errors, don't retry
                    error_text = await response.text()
                    return {
                        'error': f'API request failed with status {response.status}: {error_text}'
                    }
            
            except asyncio.TimeoutError:
                if attempt < self.retry_config['max_retries']:
                    wait_time = self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt)
                    logger.warning(f"Request timeout, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                return {'error': 'Request timeout after all retries'}
            
            except Exception as e:
                if attempt < self.retry_config['max_retries']:
                    wait_time = self.retry_config['base_delay'] * (self.retry_config['exponential_base'] ** attempt)
                    logger.warning(f"Request failed: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                return {'error': f'Request failed: {str(e)}'}
        
        return {'error': 'Max retries exceeded'}
    
    def _parse_response(self, response: Dict[str, Any], concept: str, difficulty: int) -> Dict[str, Any]:
        """Parse LLM response and extract question and answer"""
        
        try:
            # Handle OpenAI API response format
            if 'choices' in response:
                content = response['choices'][0]['message']['content']
            elif 'response' in response:
                content = response['response']
            else:
                content = str(response)
            
            # Extract question and answer using regex
            question_match = re.search(r'QUESTION:\s*(.+?)(?=EXPECTED_ANSWER:|$)', content, re.DOTALL | re.IGNORECASE)
            answer_match = re.search(r'EXPECTED_ANSWER:\s*(.+?)(?=$)', content, re.DOTALL | re.IGNORECASE)
            
            question = question_match.group(1).strip() if question_match else None
            expected_answer = answer_match.group(1).strip() if answer_match else None
            
            # Fallback parsing if structured format not found
            if not question or not expected_answer:
                lines = content.strip().split('\n')
                lines = [line.strip() for line in lines if line.strip()]
                
                if len(lines) >= 2:
                    # Try to identify question and answer from content
                    question_candidates = [line for line in lines if '?' in line or line.lower().startswith(('what', 'how', 'why', 'when', 'where', 'which'))]
                    if question_candidates:
                        question = question_candidates[0]
                        # Find the longest line as potential answer
                        answer_candidates = [line for line in lines if line != question and len(line) > 50]
                        if answer_candidates:
                            expected_answer = max(answer_candidates, key=len)
                    
                    if not question and lines:
                        question = lines[0]
                    if not expected_answer and len(lines) > 1:
                        expected_answer = ' '.join(lines[1:])
            
            # Clean up the extracted text
            if question:
                question = self._clean_text(question)
            if expected_answer:
                expected_answer = self._clean_text(expected_answer)
            
            result = {
                'question': question,
                'expected_answer': expected_answer,
                'concept': concept,
                'difficulty': difficulty,
                'generated_at': datetime.utcnow().isoformat(),
                'question_length': len(question) if question else 0,
                'answer_length': len(expected_answer) if expected_answer else 0
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                'error': f'Failed to parse response: {str(e)}',
                'question': None,
                'expected_answer': None
            }
    
    def _clean_text(self, text: str) -> str:
        """Clean and sanitize extracted text"""
        if not text:
            return ""
        
        # Remove common formatting artifacts
        text = re.sub(r'^(QUESTION|EXPECTED_ANSWER):\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\d+\.\s*', '', text)  # Remove numbering
        text = re.sub(r'^[-*]\s*', '', text)   # Remove bullet points
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove incomplete sentences at the end
        if text and not text.endswith(('.', '!', '?', ';', ':')):
            # Find the last complete sentence
            sentences = re.split(r'[.!?]+', text)
            if len(sentences) > 1:
                text = '.'.join(sentences[:-1]) + '.'
        
        return text
    
    def _validate_question_quality(self, result: Dict[str, Any]) -> bool:
        """Validate that the generated question meets quality standards"""
        
        question = result.get('question')
        expected_answer = result.get('expected_answer')
        concept = result.get('concept', '')
        
        if not question or not expected_answer:
            return False
        
        # Length validation
        if not (100 <= len(question) <= 500):
            logger.debug(f"Question length {len(question)} outside valid range (100-500)")
            return False
        
        if not (200 <= len(expected_answer) <= 1000):
            logger.debug(f"Answer length {len(expected_answer)} outside valid range (200-1000)")
            return False
        
        # Quality checks
        if not question.strip().endswith('?'):
            logger.debug("Question does not end with question mark")
            return False
        
        # Check for completeness
        incomplete_indicators = ['...', 'etc.', '[', 'TODO', 'PLACEHOLDER']
        if any(indicator in question.lower() for indicator in incomplete_indicators):
            logger.debug("Question contains incomplete indicators")
            return False
        
        if any(indicator in expected_answer.lower() for indicator in incomplete_indicators):
            logger.debug("Answer contains incomplete indicators")
            return False
        
        # Concept relevance check (basic)
        if concept and len(concept) > 3:
            concept_words = concept.lower().split()
            content_lower = (question + ' ' + expected_answer).lower()
            relevance_score = sum(1 for word in concept_words if word in content_lower) / len(concept_words)
            
            if relevance_score < 0.3:  # At least 30% of concept words should appear
                logger.debug(f"Low concept relevance score: {relevance_score}")
                return False
        
        return True
    
    def _generate_cache_key(
        self, 
        chunk_content: str, 
        concept: str, 
        difficulty: int, 
        context: str,
        question_type: str
    ) -> str:
        """Generate cache key for question"""
        content_hash = hashlib.md5(
            f"{chunk_content}:{concept}:{difficulty}:{context}:{question_type}".encode()
        ).hexdigest()
        return f"llm_question:{content_hash}"
    
    async def generate_multiple_questions(
        self,
        chunk_content: str,
        concept: str,
        count: int = 3,
        difficulty_range: tuple = (2, 4),
        question_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate multiple questions for the same content"""
        
        if question_types is None:
            question_types = ["comprehension", "application", "analysis"]
        
        questions = []
        tasks = []
        
        for i in range(count):
            difficulty = difficulty_range[0] + (i % (difficulty_range[1] - difficulty_range[0] + 1))
            question_type = question_types[i % len(question_types)]
            
            task = self.generate_question(
                chunk_content=chunk_content,
                concept=concept,
                difficulty=difficulty,
                question_type=question_type
            )
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in batch question generation: {result}")
                continue
            
            if result.get('question') and result.get('expected_answer'):
                questions.append(result)
        
        return questions


class CircuitBreaker:
    """Simple circuit breaker for API resilience"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution"""
        if self.state == 'CLOSED':
            return True
        
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                return True
            return False
        
        if self.state == 'HALF_OPEN':
            return True
        
        return False
    
    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


# Create singleton instance
llm_service = LLMService()