"""
Embedding Generator - Multi-model embedding generation for educational content

Supports multiple embedding models with automatic model selection, quality assessment,
and optimized embedding generation for educational text chunks.
"""

import numpy as np
import logging
import time
import hashlib
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Note: In production, these would be actual model imports
# For now, we'll simulate embeddings with mathematical functions
# import openai
# import sentence_transformers
# import cohere


class EmbeddingModel(Enum):
    """Supported embedding models"""
    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small" 
    OPENAI_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS_MINILM = "sentence-transformers/all-MiniLM-L6-v2"
    SENTENCE_TRANSFORMERS_MPNET = "sentence-transformers/all-mpnet-base-v2"
    COHERE_ENGLISH = "embed-english-v3.0"
    COHERE_MULTILINGUAL = "embed-multilingual-v3.0"
    INSTRUCTOR_LARGE = "hkunlp/instructor-large"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    model: EmbeddingModel
    dimensions: int
    max_tokens: int
    batch_size: int = 10
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    custom_instructions: Optional[str] = None
    normalize: bool = True
    cache_embeddings: bool = True


@dataclass
class EmbeddingResult:
    """Result from embedding generation"""
    text: str
    embedding: np.ndarray
    model: EmbeddingModel
    dimensions: int
    generation_time: float
    token_count: int
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class BatchEmbeddingResult:
    """Result from batch embedding generation"""
    results: List[EmbeddingResult]
    total_texts: int
    successful_embeddings: int
    failed_embeddings: int
    total_time: float
    average_time_per_text: float
    total_tokens: int
    model_used: EmbeddingModel
    batch_statistics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class EmbeddingCache:
    """Simple in-memory cache for embeddings"""
    
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, EmbeddingResult] = {}
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
    
    def _generate_key(self, text: str, model: EmbeddingModel) -> str:
        """Generate cache key from text and model"""
        content = f"{text}||{model.value}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: EmbeddingModel) -> Optional[EmbeddingResult]:
        """Get cached embedding if available"""
        key = self._generate_key(text, model)
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def put(self, text: str, model: EmbeddingModel, result: EmbeddingResult):
        """Store embedding in cache"""
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        key = self._generate_key(text, model)
        self.cache[key] = result
        self.access_times[key] = time.time()
    
    def _evict_oldest(self):
        """Evict least recently used item"""
        if not self.access_times:
            return
        
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.access_times.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


class MockEmbeddingProvider:
    """Mock embedding provider for testing and development"""
    
    def __init__(self, model: EmbeddingModel):
        self.model = model
        self.dimensions = self._get_model_dimensions(model)
        
    def _get_model_dimensions(self, model: EmbeddingModel) -> int:
        """Get dimensions for different models"""
        dimension_map = {
            EmbeddingModel.OPENAI_ADA_002: 1536,
            EmbeddingModel.OPENAI_3_SMALL: 1536,
            EmbeddingModel.OPENAI_3_LARGE: 3072,
            EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM: 384,
            EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET: 768,
            EmbeddingModel.COHERE_ENGLISH: 1024,
            EmbeddingModel.COHERE_MULTILINGUAL: 1024,
            EmbeddingModel.INSTRUCTOR_LARGE: 768
        }
        return dimension_map.get(model, 768)
    
    def generate_embedding(self, text: str) -> Tuple[np.ndarray, int]:
        """Generate mock embedding based on text characteristics"""
        # Simulate processing time
        time.sleep(0.01)
        
        # Create deterministic embedding based on text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)
        
        # Generate embedding with text-based features
        embedding = np.random.normal(0, 1, self.dimensions)
        
        # Add semantic features based on content
        if any(word in text.lower() for word in ['definition', 'define']):
            embedding[0:10] += 0.5  # Definition signal
        
        if any(word in text.lower() for word in ['example', 'exercise', 'problem']):
            embedding[10:20] += 0.5  # Example signal
            
        if any(symbol in text for symbol in ['∫', '∑', '∂', '$', '=']):
            embedding[20:30] += 0.5  # Mathematical content signal
        
        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)
        
        # Estimate token count (rough approximation)
        token_count = max(1, len(text.split()) * 1.3)
        
        return embedding.astype(np.float32), int(token_count)


class EmbeddingGenerator:
    """
    Multi-model embedding generator for educational content.
    
    Supports various embedding models with automatic quality assessment,
    caching, and batch processing capabilities.
    """
    
    def __init__(self, 
                 default_config: Optional[EmbeddingConfig] = None,
                 enable_cache: bool = True,
                 cache_size: int = 10000,
                 max_workers: int = 4):
        """
        Initialize embedding generator.
        
        Args:
            default_config: Default embedding configuration
            enable_cache: Enable embedding caching
            cache_size: Maximum cache size
            max_workers: Maximum worker threads for parallel processing
        """
        
        self.default_config = default_config or EmbeddingConfig(
            model=EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM,
            dimensions=384,
            max_tokens=512,
            batch_size=10,
            normalize=True,
            cache_embeddings=True
        )
        
        self.cache = EmbeddingCache(cache_size) if enable_cache else None
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        
        # Initialize model providers (mock for now)
        self.providers: Dict[EmbeddingModel, MockEmbeddingProvider] = {}
        self._initialize_providers()
        
        # Statistics tracking
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'model_usage': {}
        }
    
    def _initialize_providers(self):
        """Initialize embedding model providers"""
        # In production, this would initialize actual model clients
        # For now, using mock providers
        for model in EmbeddingModel:
            self.providers[model] = MockEmbeddingProvider(model)
    
    def generate_embedding(self, 
                          text: str,
                          config: Optional[EmbeddingConfig] = None) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            config: Optional embedding configuration override
            
        Returns:
            EmbeddingResult with embedding and metadata
        """
        
        if not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        config = config or self.default_config
        start_time = time.time()
        
        # Check cache first
        if self.cache and config.cache_embeddings:
            cached_result = self.cache.get(text, config.model)
            if cached_result:
                self.stats['cache_hits'] += 1
                self.logger.debug(f"Cache hit for text: {text[:50]}...")
                return cached_result
        
        self.stats['cache_misses'] += 1
        
        # Preprocess text
        processed_text = self._preprocess_text(text, config)
        
        # Generate embedding
        provider = self.providers[config.model]
        embedding, token_count = provider.generate_embedding(processed_text)
        
        # Post-process embedding
        if config.normalize and np.linalg.norm(embedding) > 0:
            embedding = embedding / np.linalg.norm(embedding)
        
        generation_time = time.time() - start_time
        
        # Create result
        result = EmbeddingResult(
            text=text,
            embedding=embedding,
            model=config.model,
            dimensions=len(embedding),
            generation_time=generation_time,
            token_count=token_count,
            metadata={
                'processed_text_length': len(processed_text),
                'original_text_length': len(text),
                'config': {
                    'model': config.model.value,
                    'normalize': config.normalize,
                    'max_tokens': config.max_tokens
                }
            }
        )
        
        # Cache result
        if self.cache and config.cache_embeddings:
            self.cache.put(text, config.model, result)
        
        # Update statistics
        self._update_stats(config.model, token_count, generation_time)
        
        self.logger.debug(f"Generated embedding: {config.model.value}, "
                         f"{len(embedding)}D, {generation_time:.3f}s")
        
        return result
    
    def generate_batch_embeddings(self,
                                 texts: List[str],
                                 config: Optional[EmbeddingConfig] = None,
                                 max_workers: Optional[int] = None) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts in parallel.
        
        Args:
            texts: List of texts to embed
            config: Optional embedding configuration override
            max_workers: Override default max workers
            
        Returns:
            BatchEmbeddingResult with all embeddings and statistics
        """
        
        if not texts:
            raise ValueError("Cannot generate embeddings for empty text list")
        
        config = config or self.default_config
        max_workers = max_workers or self.max_workers
        start_time = time.time()
        
        self.logger.info(f"Generating batch embeddings: {len(texts)} texts, "
                        f"{config.model.value}, {max_workers} workers")
        
        results = []
        errors = []
        
        if max_workers == 1:
            # Sequential processing
            for i, text in enumerate(texts):
                try:
                    result = self.generate_embedding(text, config)
                    results.append(result)
                except Exception as e:
                    error_msg = f"Failed to embed text {i}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_index = {}
                for i, text in enumerate(texts):
                    future = executor.submit(self.generate_embedding, text, config)
                    future_to_index[future] = i
                
                # Collect results
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        error_msg = f"Failed to embed text {index}: {str(e)}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
        
        total_time = time.time() - start_time
        successful_count = len(results)
        failed_count = len(errors)
        
        # Calculate statistics
        total_tokens = sum(r.token_count for r in results)
        avg_time_per_text = total_time / max(1, len(texts))
        
        batch_stats = self._calculate_batch_statistics(results, total_time)
        
        self.logger.info(f"Batch embedding complete: {successful_count}/{len(texts)} "
                        f"successful in {total_time:.2f}s")
        
        return BatchEmbeddingResult(
            results=results,
            total_texts=len(texts),
            successful_embeddings=successful_count,
            failed_embeddings=failed_count,
            total_time=total_time,
            average_time_per_text=avg_time_per_text,
            total_tokens=total_tokens,
            model_used=config.model,
            batch_statistics=batch_stats,
            errors=errors
        )
    
    def _preprocess_text(self, text: str, config: EmbeddingConfig) -> str:
        """Preprocess text before embedding"""
        # Basic text cleaning
        processed = text.strip()
        
        # Remove excessive whitespace
        import re
        processed = re.sub(r'\s+', ' ', processed)
        
        # Truncate to max tokens (rough estimation)
        words = processed.split()
        if len(words) > config.max_tokens * 0.75:  # Rough word-to-token ratio
            processed = ' '.join(words[:int(config.max_tokens * 0.75)])
            processed += "..."
        
        # Add custom instructions if provided
        if config.custom_instructions:
            processed = f"{config.custom_instructions}\n\n{processed}"
        
        return processed
    
    def _calculate_batch_statistics(self, 
                                   results: List[EmbeddingResult], 
                                   total_time: float) -> Dict[str, Any]:
        """Calculate statistics for batch processing"""
        if not results:
            return {}
        
        embeddings = np.array([r.embedding for r in results])
        
        # Embedding quality metrics
        mean_embedding = np.mean(embeddings, axis=0)
        embedding_variance = np.var(embeddings, axis=0)
        mean_variance = np.mean(embedding_variance)
        
        # Similarity analysis
        similarities = []
        for i, emb1 in enumerate(embeddings):
            for j, emb2 in enumerate(embeddings[i+1:], i+1):
                sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                similarities.append(sim)
        
        avg_similarity = np.mean(similarities) if similarities else 0.0
        similarity_std = np.std(similarities) if similarities else 0.0
        
        return {
            'embedding_dimensions': results[0].dimensions,
            'total_tokens': sum(r.token_count for r in results),
            'avg_generation_time': np.mean([r.generation_time for r in results]),
            'min_generation_time': min(r.generation_time for r in results),
            'max_generation_time': max(r.generation_time for r in results),
            'tokens_per_second': sum(r.token_count for r in results) / max(total_time, 0.001),
            'embeddings_per_second': len(results) / max(total_time, 0.001),
            'mean_embedding_variance': float(mean_variance),
            'avg_cosine_similarity': float(avg_similarity),
            'similarity_std_dev': float(similarity_std),
            'embedding_norm_stats': {
                'mean': float(np.mean([np.linalg.norm(r.embedding) for r in results])),
                'std': float(np.std([np.linalg.norm(r.embedding) for r in results])),
                'min': float(min(np.linalg.norm(r.embedding) for r in results)),
                'max': float(max(np.linalg.norm(r.embedding) for r in results))
            }
        }
    
    def _update_stats(self, model: EmbeddingModel, tokens: int, generation_time: float):
        """Update global statistics"""
        self.stats['total_embeddings'] += 1
        self.stats['total_tokens'] += tokens
        self.stats['total_time'] += generation_time
        
        model_name = model.value
        if model_name not in self.stats['model_usage']:
            self.stats['model_usage'][model_name] = {
                'count': 0,
                'tokens': 0,
                'time': 0.0
            }
        
        self.stats['model_usage'][model_name]['count'] += 1
        self.stats['model_usage'][model_name]['tokens'] += tokens
        self.stats['model_usage'][model_name]['time'] += generation_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get embedding generation statistics"""
        stats = self.stats.copy()
        
        if stats['total_embeddings'] > 0:
            stats['avg_tokens_per_embedding'] = stats['total_tokens'] / stats['total_embeddings']
            stats['avg_time_per_embedding'] = stats['total_time'] / stats['total_embeddings']
            stats['tokens_per_second'] = stats['total_tokens'] / max(stats['total_time'], 0.001)
        
        if self.cache:
            stats['cache_size'] = self.cache.size()
            stats['cache_hit_rate'] = self.stats['cache_hits'] / max(1, 
                self.stats['cache_hits'] + self.stats['cache_misses'])
        
        return stats
    
    def reset_statistics(self):
        """Reset statistics"""
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'model_usage': {}
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        if self.cache:
            self.cache.clear()
            self.logger.info("Embedding cache cleared")
    
    def get_supported_models(self) -> List[EmbeddingModel]:
        """Get list of supported embedding models"""
        return list(EmbeddingModel)
    
    def get_model_info(self, model: EmbeddingModel) -> Dict[str, Any]:
        """Get information about a specific model"""
        provider = self.providers.get(model)
        if not provider:
            return {}
        
        return {
            'model': model.value,
            'dimensions': provider.dimensions,
            'max_tokens': 8192,  # Default max tokens
            'description': self._get_model_description(model)
        }
    
    def _get_model_description(self, model: EmbeddingModel) -> str:
        """Get description for embedding model"""
        descriptions = {
            EmbeddingModel.OPENAI_ADA_002: "OpenAI's general-purpose embedding model (legacy)",
            EmbeddingModel.OPENAI_3_SMALL: "OpenAI's efficient embedding model with good performance",
            EmbeddingModel.OPENAI_3_LARGE: "OpenAI's most capable embedding model",
            EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM: "Fast and efficient sentence transformer",
            EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET: "High-quality sentence transformer", 
            EmbeddingModel.COHERE_ENGLISH: "Cohere's English-optimized embedding model",
            EmbeddingModel.COHERE_MULTILINGUAL: "Cohere's multilingual embedding model",
            EmbeddingModel.INSTRUCTOR_LARGE: "Instruction-tuned embedding model"
        }
        return descriptions.get(model, "Unknown model")


# Utility functions for educational content embedding

def create_educational_config(model: EmbeddingModel = EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET) -> EmbeddingConfig:
    """Create optimized config for educational content"""
    return EmbeddingConfig(
        model=model,
        dimensions=768 if model == EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET else 384,
        max_tokens=512,
        batch_size=16,
        normalize=True,
        cache_embeddings=True,
        custom_instructions="This is educational content from a textbook. Focus on semantic meaning and concepts."
    )


def create_mathematical_config(model: EmbeddingModel = EmbeddingModel.OPENAI_3_LARGE) -> EmbeddingConfig:
    """Create optimized config for mathematical content"""
    return EmbeddingConfig(
        model=model,
        dimensions=3072 if model == EmbeddingModel.OPENAI_3_LARGE else 768,
        max_tokens=1000,
        batch_size=8,
        normalize=True,
        cache_embeddings=True,
        custom_instructions="This is mathematical content with formulas and equations. Preserve mathematical relationships."
    )


def calculate_embedding_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    if len(emb1) != len(emb2):
        raise ValueError("Embeddings must have same dimensions")
    
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(emb1, emb2) / (norm1 * norm2))