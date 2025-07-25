"""
Embedding service for academic content
Uses OpenAI or sentence-transformers for vector generation
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from openai import AsyncOpenAI
import asyncio
from functools import lru_cache

from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings from text"""
    
    def __init__(self):
        self.openai_client = None
        self.local_model = None
        self.use_openai = bool(settings.openai_api_key)
        
    async def initialize(self):
        """Initialize embedding models"""
        if self.use_openai:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info("Initialized OpenAI embeddings")
        else:
            # Fallback to local model
            try:
                from sentence_transformers import SentenceTransformer
                self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Initialized local sentence-transformers model")
            except ImportError:
                logger.warning("No embedding model available")
    
    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        if not text:
            return None
        
        try:
            if self.use_openai and self.openai_client:
                # Use OpenAI embeddings
                response = await self.openai_client.embeddings.create(
                    input=text,
                    model=model
                )
                return response.data[0].embedding
            
            elif self.local_model:
                # Use local model (run in thread to avoid blocking)
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,
                    lambda: self.local_model.encode(text).tolist()
                )
                return embedding
            
            else:
                logger.error("No embedding model available")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small"
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        if not texts:
            return []
        
        try:
            if self.use_openai and self.openai_client:
                # OpenAI supports batch processing
                response = await self.openai_client.embeddings.create(
                    input=texts,
                    model=model
                )
                return [item.embedding for item in response.data]
            
            elif self.local_model:
                # Use local model with batching
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.local_model.encode(texts).tolist()
                )
                return embeddings
            
            else:
                return [None] * len(texts)
                
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)
    
    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 10
    ) -> List[tuple[int, float]]:
        """Find most similar embeddings from candidates"""
        if not candidate_embeddings:
            return []
        
        similarities = []
        for idx, candidate in enumerate(candidate_embeddings):
            sim = self.cosine_similarity(query_embedding, candidate)
            similarities.append((idx, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    async def generate_concept_embedding(
        self,
        concept_data: Dict[str, Any]
    ) -> Optional[List[float]]:
        """Generate embedding for a learning concept"""
        # Combine relevant fields for embedding
        text_parts = []
        
        if concept_data.get('title'):
            text_parts.append(f"Title: {concept_data['title']}")
        
        if concept_data.get('description'):
            text_parts.append(f"Description: {concept_data['description']}")
        
        if concept_data.get('learning_objectives'):
            objectives = ' '.join(concept_data['learning_objectives'])
            text_parts.append(f"Learning objectives: {objectives}")
        
        if concept_data.get('tags'):
            tags = ' '.join(concept_data['tags'])
            text_parts.append(f"Tags: {tags}")
        
        combined_text = ' '.join(text_parts)
        return await self.generate_embedding(combined_text)
    
    async def generate_query_embedding(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embedding for a search query with optional context"""
        if context:
            combined = f"Query: {query}\nContext: {context}"
        else:
            combined = query
        
        return await self.generate_embedding(combined)
    
    @lru_cache(maxsize=1000)
    def get_embedding_dimension(self, model: str = "text-embedding-3-small") -> int:
        """Get the dimension of embeddings for a model"""
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768
        }
        
        if self.local_model:
            # Get dimension from loaded model
            try:
                return self.local_model.get_sentence_embedding_dimension()
            except:
                pass
        
        return dimensions.get(model, 1536)


# Create singleton instance
embedding_service = EmbeddingService()