"""
Academic sentence generation service
Uses OpenAI GPT models for generating learning content
"""

import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import json

from ..config import settings

logger = logging.getLogger(__name__)


class GenerationService:
    """Service for generating academic content and learning materials"""
    
    def __init__(self):
        self.client = None
        self.enabled = bool(settings.openai_api_key)
        
    async def initialize(self):
        """Initialize OpenAI client"""
        if self.enabled:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("Initialized OpenAI generation service")
        else:
            logger.warning("OpenAI API key not configured, generation features disabled")
    
    async def generate_academic_sentence(
        self,
        topic: str,
        style: str = "explanatory",
        difficulty: str = "intermediate",
        max_length: int = 150
    ) -> Optional[str]:
        """Generate an academic sentence about a topic"""
        if not self.enabled:
            return None
        
        style_prompts = {
            "explanatory": "Write a clear explanatory sentence",
            "technical": "Write a technical, precise sentence",
            "introductory": "Write an introductory sentence for beginners",
            "advanced": "Write an advanced, scholarly sentence",
            "summary": "Write a concise summary sentence"
        }
        
        try:
            prompt = f"{style_prompts.get(style, style_prompts['explanatory'])} about '{topic}' at a {difficulty} level. Keep it under {max_length} characters."
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert academic writer creating educational content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate academic sentence: {e}")
            return None
    
    async def generate_practice_questions(
        self,
        concept: str,
        description: str,
        difficulty: str = "intermediate",
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate practice questions for a concept"""
        if not self.enabled:
            return []
        
        try:
            prompt = f"""Generate {count} practice questions for the concept: '{concept}'
Description: {description}
Difficulty level: {difficulty}

Format as JSON array with each question having:
- question: The question text
- type: 'multiple_choice' or 'short_answer' or 'true_false'
- options: Array of options (for multiple choice)
- correct_answer: The correct answer
- explanation: Brief explanation of the answer
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an educational content creator generating practice questions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Ensure we return a list
            if isinstance(result, dict) and 'questions' in result:
                return result['questions']
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to generate practice questions: {e}")
            return []
    
    async def generate_learning_objectives(
        self,
        topic: str,
        level: str = "intermediate",
        count: int = 4
    ) -> List[str]:
        """Generate learning objectives for a topic"""
        if not self.enabled:
            return []
        
        try:
            prompt = f"""Generate {count} clear, measurable learning objectives for the topic: '{topic}'
Level: {level}

Use action verbs like: understand, analyze, apply, create, evaluate, explain.
Format as a simple list of objectives."""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an instructional designer creating learning objectives."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            # Parse bullet points or numbered lists
            objectives = [
                line.strip().lstrip('•-*123456789. ')
                for line in content.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]
            
            return objectives[:count]
            
        except Exception as e:
            logger.error(f"Failed to generate learning objectives: {e}")
            return []
    
    async def generate_concept_explanation(
        self,
        concept: str,
        context: Optional[str] = None,
        max_length: int = 500
    ) -> Optional[str]:
        """Generate a detailed explanation of a concept"""
        if not self.enabled:
            return None
        
        try:
            prompt = f"Explain the concept '{concept}' clearly and concisely."
            if context:
                prompt += f" Context: {context}"
            prompt += f" Keep the explanation under {max_length} characters."
            
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert educator explaining concepts clearly."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate concept explanation: {e}")
            return None
    
    async def generate_learning_path_suggestions(
        self,
        current_concept: str,
        student_level: str,
        completed_concepts: List[str]
    ) -> List[Dict[str, str]]:
        """Generate suggestions for next concepts in learning path"""
        if not self.enabled:
            return []
        
        try:
            completed = ', '.join(completed_concepts) if completed_concepts else "none"
            
            prompt = f"""Given that a student at {student_level} level is currently learning '{current_concept}' 
and has completed: {completed}

Suggest 3-5 next concepts they should learn, ordered by recommended sequence.
Format as JSON array with:
- concept: Name of the concept
- reason: Why this is a good next step
- difficulty: relative difficulty (easier, similar, harder)
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an educational advisor suggesting learning paths."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            if isinstance(result, dict) and 'suggestions' in result:
                return result['suggestions']
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to generate learning path suggestions: {e}")
            return []
    
    async def generate_prerequisite_check(
        self,
        concept: str,
        description: str
    ) -> List[str]:
        """Generate list of prerequisite concepts"""
        if not self.enabled:
            return []
        
        try:
            prompt = f"""For the concept '{concept}' ({description}), 
list the essential prerequisite concepts a student should know first.
Return only concept names, one per line."""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert in curriculum design identifying prerequisites."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.6
            )
            
            content = response.choices[0].message.content
            prerequisites = [
                line.strip().lstrip('•-*123456789. ')
                for line in content.split('\n')
                if line.strip()
            ]
            
            return prerequisites
            
        except Exception as e:
            logger.error(f"Failed to generate prerequisites: {e}")
            return []


# Create singleton instance
generation_service = GenerationService()