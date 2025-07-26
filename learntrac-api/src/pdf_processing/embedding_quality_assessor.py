"""
Embedding Quality Assessor - Comprehensive quality assessment for educational embeddings

Evaluates embedding quality using multiple metrics including semantic coherence, 
dimensionality analysis, clustering quality, and educational content appropriateness.
"""

import numpy as np
import logging
import time
from typing import List, Dict, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict

from .embedding_generator import EmbeddingResult, EmbeddingModel
from .chunk_metadata import ChunkMetadata, ContentType


class QualityMetric(Enum):
    """Types of quality metrics"""
    SEMANTIC_COHERENCE = "semantic_coherence"
    DIMENSIONALITY_USAGE = "dimensionality_usage"
    CLUSTERING_QUALITY = "clustering_quality"
    EDUCATIONAL_APPROPRIATENESS = "educational_appropriateness"
    MATHEMATICAL_PRESERVATION = "mathematical_preservation"
    DEFINITION_CLARITY = "definition_clarity"
    EXAMPLE_DISTINCTION = "example_distinction"
    CONTENT_TYPE_SEPARATION = "content_type_separation"


@dataclass
class QualityScore:
    """Individual quality metric score"""
    metric: QualityMetric
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class EmbeddingQualityAssessment:
    """Complete quality assessment for embeddings"""
    overall_quality: float  # 0.0 to 1.0
    quality_grade: str  # A, B, C, D, F
    individual_scores: List[QualityScore]
    model_evaluation: Dict[str, Any]
    content_analysis: Dict[str, Any]
    recommendations: List[str]
    assessment_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchQualityAssessment:
    """Quality assessment for batch of embeddings"""
    individual_assessments: List[EmbeddingQualityAssessment]
    batch_statistics: Dict[str, Any]
    quality_distribution: Dict[str, int]  # Grade -> count
    model_comparison: Dict[str, Any]
    overall_batch_quality: float
    batch_recommendations: List[str]
    assessment_time: float


class EmbeddingQualityAssessor:
    """
    Comprehensive quality assessment for educational embeddings.
    
    Evaluates embeddings across multiple dimensions including semantic coherence,
    educational appropriateness, and content-specific quality metrics.
    """
    
    def __init__(self,
                 quality_threshold: float = 0.7,
                 enable_detailed_analysis: bool = True,
                 educational_weight: float = 0.3,
                 semantic_weight: float = 0.4,
                 technical_weight: float = 0.3):
        """
        Initialize quality assessor.
        
        Args:
            quality_threshold: Minimum quality score for acceptance
            enable_detailed_analysis: Enable detailed quality analysis
            educational_weight: Weight for educational appropriateness
            semantic_weight: Weight for semantic quality
            technical_weight: Weight for technical quality
        """
        
        self.quality_threshold = quality_threshold
        self.enable_detailed_analysis = enable_detailed_analysis
        self.educational_weight = educational_weight
        self.semantic_weight = semantic_weight
        self.technical_weight = technical_weight
        
        self.logger = logging.getLogger(__name__)
        
        # Quality assessment statistics
        self.assessment_stats = {
            'total_assessments': 0,
            'quality_distribution': defaultdict(int),
            'average_quality': 0.0,
            'model_performance': defaultdict(list),
            'content_type_quality': defaultdict(list)
        }
    
    def assess_embedding_quality(self,
                                embedding_result: EmbeddingResult,
                                chunk_metadata: Optional[ChunkMetadata] = None) -> EmbeddingQualityAssessment:
        """
        Assess quality of a single embedding.
        
        Args:
            embedding_result: Embedding result to assess
            chunk_metadata: Optional metadata about the source chunk
            
        Returns:
            EmbeddingQualityAssessment with detailed quality analysis
        """
        
        start_time = time.time()
        
        self.logger.debug(f"Assessing embedding quality: {embedding_result.model.value}, "
                         f"{embedding_result.dimensions}D")
        
        # Calculate individual quality metrics
        quality_scores = []
        
        # Semantic coherence
        semantic_score = self._assess_semantic_coherence(embedding_result, chunk_metadata)
        quality_scores.append(semantic_score)
        
        # Dimensionality usage
        dimensionality_score = self._assess_dimensionality_usage(embedding_result)
        quality_scores.append(dimensionality_score)
        
        # Educational appropriateness
        if chunk_metadata:
            educational_score = self._assess_educational_appropriateness(
                embedding_result, chunk_metadata
            )
            quality_scores.append(educational_score)
        
        # Content type specific assessments
        if chunk_metadata:
            content_scores = self._assess_content_type_quality(
                embedding_result, chunk_metadata
            )
            quality_scores.extend(content_scores)
        
        # Calculate overall quality
        overall_quality = self._calculate_overall_quality(quality_scores)
        quality_grade = self._assign_quality_grade(overall_quality)
        
        # Generate model evaluation
        model_evaluation = self._evaluate_model_performance(embedding_result)
        
        # Generate content analysis
        content_analysis = self._analyze_content_characteristics(
            embedding_result, chunk_metadata
        )
        
        # Generate recommendations
        recommendations = self._generate_quality_recommendations(
            quality_scores, overall_quality, embedding_result, chunk_metadata
        )
        
        assessment_time = time.time() - start_time
        
        # Create assessment
        assessment = EmbeddingQualityAssessment(
            overall_quality=overall_quality,
            quality_grade=quality_grade,
            individual_scores=quality_scores,
            model_evaluation=model_evaluation,
            content_analysis=content_analysis,
            recommendations=recommendations,
            assessment_metadata={
                'assessment_time': assessment_time,
                'assessor_version': '1.0',
                'threshold_used': self.quality_threshold,
                'weights': {
                    'educational': self.educational_weight,
                    'semantic': self.semantic_weight,
                    'technical': self.technical_weight
                }
            }
        )
        
        # Update statistics
        self._update_assessment_stats(assessment, embedding_result, chunk_metadata)
        
        self.logger.debug(f"Quality assessment complete: {quality_grade} "
                         f"({overall_quality:.3f}) in {assessment_time:.3f}s")
        
        return assessment
    
    def assess_batch_quality(self,
                           embedding_results: List[EmbeddingResult],
                           chunk_metadata_list: Optional[List[ChunkMetadata]] = None) -> BatchQualityAssessment:
        """
        Assess quality of multiple embeddings.
        
        Args:
            embedding_results: List of embedding results
            chunk_metadata_list: Optional list of chunk metadata
            
        Returns:
            BatchQualityAssessment with comprehensive batch analysis
        """
        
        import time
        start_time = time.time()
        
        if not embedding_results:
            raise ValueError("Cannot assess quality of empty embedding list")
        
        self.logger.info(f"Assessing batch quality: {len(embedding_results)} embeddings")
        
        # Assess individual embeddings
        individual_assessments = []
        for i, embedding_result in enumerate(embedding_results):
            chunk_metadata = None
            if chunk_metadata_list and i < len(chunk_metadata_list):
                chunk_metadata = chunk_metadata_list[i]
            
            assessment = self.assess_embedding_quality(embedding_result, chunk_metadata)
            individual_assessments.append(assessment)
        
        # Calculate batch statistics
        batch_statistics = self._calculate_batch_statistics(
            individual_assessments, embedding_results
        )
        
        # Calculate quality distribution
        quality_distribution = defaultdict(int)
        for assessment in individual_assessments:
            quality_distribution[assessment.quality_grade] += 1
        
        # Compare models if multiple models used
        model_comparison = self._compare_models_in_batch(
            individual_assessments, embedding_results
        )
        
        # Calculate overall batch quality
        quality_scores = [a.overall_quality for a in individual_assessments]
        overall_batch_quality = statistics.mean(quality_scores)
        
        # Generate batch recommendations
        batch_recommendations = self._generate_batch_recommendations(
            individual_assessments, batch_statistics, model_comparison
        )
        
        assessment_time = time.time() - start_time
        
        self.logger.info(f"Batch quality assessment complete: "
                        f"{overall_batch_quality:.3f} average quality")
        
        return BatchQualityAssessment(
            individual_assessments=individual_assessments,
            batch_statistics=batch_statistics,
            quality_distribution=dict(quality_distribution),
            model_comparison=model_comparison,
            overall_batch_quality=overall_batch_quality,
            batch_recommendations=batch_recommendations,
            assessment_time=assessment_time
        )
    
    def _assess_semantic_coherence(self,
                                 embedding_result: EmbeddingResult,
                                 chunk_metadata: Optional[ChunkMetadata]) -> QualityScore:
        """Assess semantic coherence of embedding"""
        
        embedding = embedding_result.embedding
        text = embedding_result.text
        
        # Analyze embedding distribution
        embedding_norm = np.linalg.norm(embedding)
        embedding_mean = np.mean(embedding)
        embedding_std = np.std(embedding)
        
        # Calculate semantic coherence score
        coherence_score = 0.8  # Base score
        
        # Adjust based on embedding characteristics
        if embedding_norm < 0.5:
            coherence_score -= 0.2  # Too weak
        elif embedding_norm > 2.0:
            coherence_score -= 0.1  # Too strong
        
        if embedding_std < 0.1:
            coherence_score -= 0.3  # Not enough variation
        elif embedding_std > 1.0:
            coherence_score -= 0.1  # Too much variation
        
        # Adjust based on text characteristics
        word_count = len(text.split())
        if word_count < 5:
            coherence_score -= 0.2  # Too short for good semantics
        elif word_count > 500:
            coherence_score -= 0.1  # May be too long
        
        coherence_score = max(0.0, min(1.0, coherence_score))
        
        details = {
            'embedding_norm': float(embedding_norm),
            'embedding_mean': float(embedding_mean),
            'embedding_std': float(embedding_std),
            'text_word_count': word_count,
            'distribution_analysis': self._analyze_embedding_distribution(embedding)
        }
        
        recommendations = []
        if coherence_score < 0.6:
            recommendations.append("Consider using a different embedding model")
            recommendations.append("Text may need preprocessing for better semantic quality")
        
        return QualityScore(
            metric=QualityMetric.SEMANTIC_COHERENCE,
            score=coherence_score,
            confidence=0.8,
            details=details,
            recommendations=recommendations
        )
    
    def _assess_dimensionality_usage(self, embedding_result: EmbeddingResult) -> QualityScore:
        """Assess how well the embedding uses its dimensional space"""
        
        embedding = embedding_result.embedding
        dimensions = len(embedding)
        
        # Analyze dimensional usage
        non_zero_dims = np.sum(np.abs(embedding) > 1e-6)
        usage_ratio = non_zero_dims / dimensions
        
        # Analyze dimensional distribution
        abs_values = np.abs(embedding)
        significant_dims = np.sum(abs_values > np.mean(abs_values))
        significance_ratio = significant_dims / dimensions
        
        # Calculate usage score
        usage_score = 0.7  # Base score
        
        if usage_ratio > 0.8:
            usage_score += 0.2  # Good dimensional usage
        elif usage_ratio < 0.3:
            usage_score -= 0.3  # Poor dimensional usage
        
        if 0.1 <= significance_ratio <= 0.4:
            usage_score += 0.1  # Good balance
        
        usage_score = max(0.0, min(1.0, usage_score))
        
        details = {
            'total_dimensions': dimensions,
            'non_zero_dimensions': int(non_zero_dims),
            'usage_ratio': float(usage_ratio),
            'significant_dimensions': int(significant_dims),
            'significance_ratio': float(significance_ratio),
            'sparsity': float(1.0 - usage_ratio)
        }
        
        recommendations = []
        if usage_ratio < 0.5:
            recommendations.append("Embedding may be too sparse - consider different model")
        if significance_ratio > 0.8:
            recommendations.append("High dimensional significance may indicate overfitting")
        
        return QualityScore(
            metric=QualityMetric.DIMENSIONALITY_USAGE,
            score=usage_score,
            confidence=0.9,
            details=details,
            recommendations=recommendations
        )
    
    def _assess_educational_appropriateness(self,
                                          embedding_result: EmbeddingResult,
                                          chunk_metadata: ChunkMetadata) -> QualityScore:
        """Assess how well embedding captures educational content"""
        
        text = embedding_result.text
        embedding = embedding_result.embedding
        content_type = chunk_metadata.content_type
        
        appropriateness_score = 0.7  # Base score
        
        # Analyze educational indicators in text
        educational_indicators = self._find_educational_indicators(text)
        
        # Adjust based on content type appropriateness
        if content_type == ContentType.DEFINITION:
            if any(indicator in text.lower() for indicator in ['definition', 'define', 'is a', 'is defined as']):
                appropriateness_score += 0.2
            if len(text.split()) < 10:
                appropriateness_score -= 0.1  # Too short for definition
        
        elif content_type == ContentType.EXAMPLE:
            if any(indicator in text.lower() for indicator in ['example', 'exercise', 'problem', 'solution']):
                appropriateness_score += 0.2
            if 'solution' in text.lower() and 'example' in text.lower():
                appropriateness_score += 0.1  # Complete example
        
        elif content_type == ContentType.MATH:
            math_symbols = set('∫∑∂∇π≈≠≤≥±∞√') & set(text)
            if math_symbols or '$' in text or '=' in text:
                appropriateness_score += 0.2
        
        # Adjust based on educational structure
        if chunk_metadata.chapter and chunk_metadata.section:
            appropriateness_score += 0.05  # Well-structured
        
        if chunk_metadata.difficulty > 0:
            # Embedding should vary with difficulty
            difficulty_signal = self._analyze_difficulty_signal(embedding, chunk_metadata.difficulty)
            appropriateness_score += difficulty_signal * 0.1
        
        appropriateness_score = max(0.0, min(1.0, appropriateness_score))
        
        details = {
            'content_type': content_type.value,
            'educational_indicators': educational_indicators,
            'difficulty_level': chunk_metadata.difficulty,
            'has_structure': bool(chunk_metadata.chapter and chunk_metadata.section),
            'confidence_from_chunking': chunk_metadata.confidence_score
        }
        
        recommendations = []
        if appropriateness_score < 0.6:
            recommendations.append("Content may need better educational context")
            recommendations.append("Consider preprocessing to emphasize educational elements")
        
        return QualityScore(
            metric=QualityMetric.EDUCATIONAL_APPROPRIATENESS,
            score=appropriateness_score,
            confidence=0.7,
            details=details,
            recommendations=recommendations
        )
    
    def _assess_content_type_quality(self,
                                   embedding_result: EmbeddingResult,
                                   chunk_metadata: ChunkMetadata) -> List[QualityScore]:
        """Assess quality specific to content type"""
        
        content_type = chunk_metadata.content_type
        quality_scores = []
        
        if content_type == ContentType.MATH:
            math_score = self._assess_mathematical_preservation(embedding_result, chunk_metadata)
            quality_scores.append(math_score)
        
        elif content_type == ContentType.DEFINITION:
            definition_score = self._assess_definition_clarity(embedding_result, chunk_metadata)
            quality_scores.append(definition_score)
        
        elif content_type == ContentType.EXAMPLE:
            example_score = self._assess_example_distinction(embedding_result, chunk_metadata)
            quality_scores.append(example_score)
        
        return quality_scores
    
    def _assess_mathematical_preservation(self,
                                        embedding_result: EmbeddingResult,
                                        chunk_metadata: ChunkMetadata) -> QualityScore:
        """Assess preservation of mathematical content in embedding"""
        
        text = embedding_result.text
        embedding = embedding_result.embedding
        
        # Analyze mathematical content
        math_symbols = set('∫∑∂∇π≈≠≤≥±∞√') & set(text)
        has_latex = '$' in text or '\\' in text
        has_equations = '=' in text and any(c.isdigit() for c in text)
        
        preservation_score = 0.6  # Base score
        
        if math_symbols:
            preservation_score += 0.2
        if has_latex:
            preservation_score += 0.2
        if has_equations:
            preservation_score += 0.1
        
        # Analyze if embedding captures mathematical structure
        math_signal_strength = self._analyze_mathematical_signal(embedding)
        preservation_score += math_signal_strength * 0.1
        
        preservation_score = max(0.0, min(1.0, preservation_score))
        
        details = {
            'math_symbols_count': len(math_symbols),
            'has_latex': has_latex,
            'has_equations': has_equations,
            'math_signal_strength': math_signal_strength,
            'detected_math_symbols': list(math_symbols)
        }
        
        recommendations = []
        if preservation_score < 0.7:
            recommendations.append("Mathematical content may not be well preserved")
            recommendations.append("Consider using specialized mathematical embedding models")
        
        return QualityScore(
            metric=QualityMetric.MATHEMATICAL_PRESERVATION,
            score=preservation_score,
            confidence=0.8,
            details=details,
            recommendations=recommendations
        )
    
    def _assess_definition_clarity(self,
                                 embedding_result: EmbeddingResult,
                                 chunk_metadata: ChunkMetadata) -> QualityScore:
        """Assess clarity of definition content in embedding"""
        
        text = embedding_result.text
        embedding = embedding_result.embedding
        
        # Analyze definition structure
        has_definition_marker = any(marker in text.lower() 
                                  for marker in ['definition', 'define', 'is defined as', 'is a'])
        has_explanation = len(text.split('.')) > 1  # Multiple sentences
        has_examples = any(word in text.lower() 
                          for word in ['example', 'for instance', 'such as'])
        
        clarity_score = 0.6  # Base score
        
        if has_definition_marker:
            clarity_score += 0.2
        if has_explanation:
            clarity_score += 0.1
        if has_examples:
            clarity_score += 0.1
        
        # Check if definition is complete
        word_count = len(text.split())
        if word_count > 15:  # Sufficient length for explanation
            clarity_score += 0.1
        elif word_count < 5:  # Too short
            clarity_score -= 0.2
        
        clarity_score = max(0.0, min(1.0, clarity_score))
        
        details = {
            'has_definition_marker': has_definition_marker,
            'has_explanation': has_explanation,
            'has_examples': has_examples,
            'word_count': word_count,
            'sentence_count': len(text.split('.'))
        }
        
        recommendations = []
        if clarity_score < 0.7:
            recommendations.append("Definition may lack clarity or completeness")
            recommendations.append("Ensure definition includes explanation and context")
        
        return QualityScore(
            metric=QualityMetric.DEFINITION_CLARITY,
            score=clarity_score,
            confidence=0.8,
            details=details,
            recommendations=recommendations
        )
    
    def _assess_example_distinction(self,
                                  embedding_result: EmbeddingResult,
                                  chunk_metadata: ChunkMetadata) -> QualityScore:
        """Assess how well examples are distinguished in embedding"""
        
        text = embedding_result.text
        embedding = embedding_result.embedding
        
        # Analyze example structure
        has_example_marker = any(marker in text.lower() 
                               for marker in ['example', 'exercise', 'problem'])
        has_solution = any(marker in text.lower() 
                          for marker in ['solution', 'answer', 'result'])
        has_steps = len([s for s in text.split('.') if s.strip()]) > 2
        
        distinction_score = 0.6  # Base score
        
        if has_example_marker:
            distinction_score += 0.2
        if has_solution:
            distinction_score += 0.2
        if has_steps:
            distinction_score += 0.1
        
        # Check for example completeness
        if has_example_marker and has_solution:
            distinction_score += 0.1  # Complete example
        
        distinction_score = max(0.0, min(1.0, distinction_score))
        
        details = {
            'has_example_marker': has_example_marker,
            'has_solution': has_solution,
            'has_steps': has_steps,
            'is_complete_example': has_example_marker and has_solution
        }
        
        recommendations = []
        if distinction_score < 0.7:
            recommendations.append("Example may lack clear structure or solution")
            recommendations.append("Ensure examples include problem and solution components")
        
        return QualityScore(
            metric=QualityMetric.EXAMPLE_DISTINCTION,
            score=distinction_score,
            confidence=0.8,
            details=details,
            recommendations=recommendations
        )
    
    def _calculate_overall_quality(self, quality_scores: List[QualityScore]) -> float:
        """Calculate overall quality from individual scores"""
        
        if not quality_scores:
            return 0.0
        
        # Weight scores by confidence and type
        weighted_sum = 0.0
        total_weight = 0.0
        
        for score in quality_scores:
            weight = score.confidence
            
            # Apply domain-specific weights
            if score.metric == QualityMetric.EDUCATIONAL_APPROPRIATENESS:
                weight *= self.educational_weight
            elif score.metric == QualityMetric.SEMANTIC_COHERENCE:
                weight *= self.semantic_weight
            else:
                weight *= self.technical_weight
            
            weighted_sum += score.score * weight
            total_weight += weight
        
        return weighted_sum / max(total_weight, 0.001)
    
    def _assign_quality_grade(self, overall_quality: float) -> str:
        """Assign letter grade based on quality score"""
        
        if overall_quality >= 0.9:
            return 'A'
        elif overall_quality >= 0.8:
            return 'B'
        elif overall_quality >= 0.7:
            return 'C'
        elif overall_quality >= 0.6:
            return 'D'
        else:
            return 'F'
    
    def _evaluate_model_performance(self, embedding_result: EmbeddingResult) -> Dict[str, Any]:
        """Evaluate model-specific performance metrics"""
        
        model = embedding_result.model
        dimensions = embedding_result.dimensions
        generation_time = embedding_result.generation_time
        
        return {
            'model_name': model.value,
            'dimensions': dimensions,
            'generation_time': generation_time,
            'tokens_per_second': embedding_result.token_count / max(generation_time, 0.001),
            'efficiency_score': self._calculate_efficiency_score(embedding_result),
            'model_appropriateness': self._assess_model_appropriateness(embedding_result)
        }
    
    def _analyze_content_characteristics(self,
                                       embedding_result: EmbeddingResult,
                                       chunk_metadata: Optional[ChunkMetadata]) -> Dict[str, Any]:
        """Analyze content characteristics"""
        
        text = embedding_result.text
        embedding = embedding_result.embedding
        
        analysis = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'sentence_count': len([s for s in text.split('.') if s.strip()]),
            'embedding_statistics': {
                'mean': float(np.mean(embedding)),
                'std': float(np.std(embedding)),
                'min': float(np.min(embedding)),
                'max': float(np.max(embedding)),
                'norm': float(np.linalg.norm(embedding))
            }
        }
        
        if chunk_metadata:
            analysis['content_metadata'] = {
                'content_type': chunk_metadata.content_type.value,
                'difficulty': chunk_metadata.difficulty,
                'confidence': chunk_metadata.confidence_score,
                'has_structure': bool(chunk_metadata.chapter and chunk_metadata.section)
            }
        
        return analysis
    
    def _generate_quality_recommendations(self,
                                        quality_scores: List[QualityScore],
                                        overall_quality: float,
                                        embedding_result: EmbeddingResult,
                                        chunk_metadata: Optional[ChunkMetadata]) -> List[str]:
        """Generate recommendations for improving quality"""
        
        recommendations = []
        
        # Collect recommendations from individual scores
        for score in quality_scores:
            recommendations.extend(score.recommendations)
        
        # Add overall recommendations
        if overall_quality < self.quality_threshold:
            recommendations.append(f"Overall quality ({overall_quality:.2f}) below threshold ({self.quality_threshold})")
            recommendations.append("Consider using a different embedding model")
        
        if embedding_result.generation_time > 5.0:
            recommendations.append("Embedding generation is slow - consider optimizing")
        
        if chunk_metadata and chunk_metadata.confidence_score < 0.5:
            recommendations.append("Source chunk has low confidence - may affect embedding quality")
        
        return list(set(recommendations))  # Remove duplicates
    
    # Helper methods
    
    def _analyze_embedding_distribution(self, embedding: np.ndarray) -> Dict[str, float]:
        """Analyze the distribution of embedding values"""
        
        return {
            'skewness': float(self._calculate_skewness(embedding)),
            'kurtosis': float(self._calculate_kurtosis(embedding)),
            'entropy': float(self._calculate_entropy(embedding)),
            'effective_dimensions': float(self._calculate_effective_dimensions(embedding))
        }
    
    def _find_educational_indicators(self, text: str) -> List[str]:
        """Find educational indicators in text"""
        
        indicators = []
        text_lower = text.lower()
        
        educational_terms = [
            'definition', 'theorem', 'proof', 'example', 'exercise', 'problem',
            'solution', 'chapter', 'section', 'figure', 'table', 'equation',
            'formula', 'concept', 'principle', 'theory', 'method', 'approach'
        ]
        
        for term in educational_terms:
            if term in text_lower:
                indicators.append(term)
        
        return indicators
    
    def _analyze_difficulty_signal(self, embedding: np.ndarray, difficulty: float) -> float:
        """Analyze if embedding varies appropriately with difficulty"""
        
        # Simple heuristic: higher difficulty should correlate with higher variance
        embedding_variance = np.var(embedding)
        expected_variance = 0.1 + difficulty * 0.2  # Scale with difficulty
        
        variance_match = 1.0 - abs(embedding_variance - expected_variance) / expected_variance
        return max(0.0, min(1.0, variance_match))
    
    def _analyze_mathematical_signal(self, embedding: np.ndarray) -> float:
        """Analyze mathematical signal strength in embedding"""
        
        # Look for patterns that might indicate mathematical content
        # This is a simplified heuristic
        high_magnitude_dims = np.sum(np.abs(embedding) > np.percentile(np.abs(embedding), 80))
        signal_strength = high_magnitude_dims / len(embedding)
        
        return min(1.0, signal_strength * 2)  # Scale to 0-1
    
    def _calculate_efficiency_score(self, embedding_result: EmbeddingResult) -> float:
        """Calculate efficiency score for embedding generation"""
        
        tokens = embedding_result.token_count
        time = embedding_result.generation_time
        dimensions = embedding_result.dimensions
        
        # Tokens per second per dimension (normalized efficiency)
        efficiency = (tokens / max(time, 0.001)) / dimensions * 1000
        
        return min(1.0, efficiency)  # Cap at 1.0
    
    def _assess_model_appropriateness(self, embedding_result: EmbeddingResult) -> float:
        """Assess how appropriate the model is for the content"""
        
        model = embedding_result.model
        text = embedding_result.text
        
        # Simple heuristics for model appropriateness
        appropriateness = 0.7  # Base score
        
        # Mathematical content
        if any(symbol in text for symbol in ['∫', '∑', '∂', '$', '=']):
            if model in [EmbeddingModel.OPENAI_3_LARGE, EmbeddingModel.INSTRUCTOR_LARGE]:
                appropriateness += 0.2  # Good for math
        
        # Educational content
        if any(term in text.lower() for term in ['definition', 'example', 'exercise']):
            if model in [EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET, EmbeddingModel.INSTRUCTOR_LARGE]:
                appropriateness += 0.2  # Good for educational
        
        return min(1.0, appropriateness)
    
    def _calculate_batch_statistics(self,
                                  assessments: List[EmbeddingQualityAssessment],
                                  embedding_results: List[EmbeddingResult]) -> Dict[str, Any]:
        """Calculate comprehensive batch statistics"""
        
        qualities = [a.overall_quality for a in assessments]
        
        return {
            'total_embeddings': len(assessments),
            'quality_statistics': {
                'mean': statistics.mean(qualities),
                'median': statistics.median(qualities),
                'std_dev': statistics.stdev(qualities) if len(qualities) > 1 else 0.0,
                'min': min(qualities),
                'max': max(qualities)
            },
            'grade_distribution': {
                grade: sum(1 for a in assessments if a.quality_grade == grade)
                for grade in ['A', 'B', 'C', 'D', 'F']
            },
            'passed_threshold': sum(1 for q in qualities if q >= self.quality_threshold),
            'failure_rate': sum(1 for q in qualities if q < self.quality_threshold) / len(qualities)
        }
    
    def _compare_models_in_batch(self,
                               assessments: List[EmbeddingQualityAssessment],
                               embedding_results: List[EmbeddingResult]) -> Dict[str, Any]:
        """Compare different models used in batch"""
        
        model_performance = defaultdict(list)
        
        for assessment, result in zip(assessments, embedding_results):
            model_performance[result.model.value].append(assessment.overall_quality)
        
        comparison = {}
        for model, qualities in model_performance.items():
            if qualities:
                comparison[model] = {
                    'count': len(qualities),
                    'mean_quality': statistics.mean(qualities),
                    'std_dev': statistics.stdev(qualities) if len(qualities) > 1 else 0.0,
                    'min_quality': min(qualities),
                    'max_quality': max(qualities)
                }
        
        return comparison
    
    def _generate_batch_recommendations(self,
                                      assessments: List[EmbeddingQualityAssessment],
                                      batch_stats: Dict[str, Any],
                                      model_comparison: Dict[str, Any]) -> List[str]:
        """Generate recommendations for batch quality improvement"""
        
        recommendations = []
        
        failure_rate = batch_stats.get('failure_rate', 0)
        if failure_rate > 0.2:
            recommendations.append(f"High failure rate ({failure_rate:.1%}) - review embedding strategy")
        
        if model_comparison and len(model_comparison) > 1:
            best_model = max(model_comparison.keys(), 
                           key=lambda m: model_comparison[m]['mean_quality'])
            recommendations.append(f"Best performing model: {best_model}")
        
        quality_std = batch_stats['quality_statistics']['std_dev']
        if quality_std > 0.15:
            recommendations.append("High quality variance - review content consistency")
        
        return recommendations
    
    def _update_assessment_stats(self,
                               assessment: EmbeddingQualityAssessment,
                               embedding_result: EmbeddingResult,
                               chunk_metadata: Optional[ChunkMetadata]):
        """Update global assessment statistics"""
        
        self.assessment_stats['total_assessments'] += 1
        self.assessment_stats['quality_distribution'][assessment.quality_grade] += 1
        
        # Update running average
        current_avg = self.assessment_stats['average_quality']
        total = self.assessment_stats['total_assessments']
        new_avg = (current_avg * (total - 1) + assessment.overall_quality) / total
        self.assessment_stats['average_quality'] = new_avg
        
        # Track model performance
        model_name = embedding_result.model.value
        self.assessment_stats['model_performance'][model_name].append(assessment.overall_quality)
        
        # Track content type quality
        if chunk_metadata:
            content_type = chunk_metadata.content_type.value
            self.assessment_stats['content_type_quality'][content_type].append(assessment.overall_quality)
    
    # Statistical helper methods
    
    def _calculate_skewness(self, data: np.ndarray) -> float:
        """Calculate skewness of data"""
        if len(data) < 3:
            return 0.0
        
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        
        skew = np.mean(((data - mean) / std) ** 3)
        return float(skew)
    
    def _calculate_kurtosis(self, data: np.ndarray) -> float:
        """Calculate kurtosis of data"""
        if len(data) < 4:
            return 0.0
        
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        
        kurt = np.mean(((data - mean) / std) ** 4) - 3
        return float(kurt)
    
    def _calculate_entropy(self, data: np.ndarray) -> float:
        """Calculate entropy of data distribution"""
        # Discretize data into bins
        hist, _ = np.histogram(data, bins=50, density=True)
        hist = hist[hist > 0]  # Remove zero bins
        
        if len(hist) == 0:
            return 0.0
        
        entropy = -np.sum(hist * np.log2(hist))
        return float(entropy)
    
    def _calculate_effective_dimensions(self, embedding: np.ndarray) -> float:
        """Calculate effective dimensionality of embedding"""
        
        # Based on participation ratio
        squared_weights = embedding ** 2
        sum_squared = np.sum(squared_weights)
        sum_fourth = np.sum(squared_weights ** 2)
        
        if sum_fourth == 0:
            return 0.0
        
        effective_dims = (sum_squared ** 2) / sum_fourth
        return float(effective_dims)
    
    def get_assessment_statistics(self) -> Dict[str, Any]:
        """Get global assessment statistics"""
        return {
            'total_assessments': self.assessment_stats['total_assessments'],
            'average_quality': self.assessment_stats['average_quality'],
            'quality_distribution': dict(self.assessment_stats['quality_distribution']),
            'model_performance': {
                model: {
                    'count': len(qualities),
                    'mean': statistics.mean(qualities) if qualities else 0,
                    'std': statistics.stdev(qualities) if len(qualities) > 1 else 0
                }
                for model, qualities in self.assessment_stats['model_performance'].items()
            },
            'content_type_performance': {
                content_type: {
                    'count': len(qualities),
                    'mean': statistics.mean(qualities) if qualities else 0,
                    'std': statistics.stdev(qualities) if len(qualities) > 1 else 0
                }
                for content_type, qualities in self.assessment_stats['content_type_quality'].items()
            }
        }
    
    def reset_statistics(self):
        """Reset assessment statistics"""
        self.assessment_stats = {
            'total_assessments': 0,
            'quality_distribution': defaultdict(int),
            'average_quality': 0.0,
            'model_performance': defaultdict(list),
            'content_type_quality': defaultdict(list)
        }


# Utility functions

def compare_embedding_quality(assessment1: EmbeddingQualityAssessment,
                            assessment2: EmbeddingQualityAssessment) -> Dict[str, Any]:
    """Compare two embedding quality assessments"""
    
    return {
        'quality_difference': assessment1.overall_quality - assessment2.overall_quality,
        'grade_comparison': (assessment1.quality_grade, assessment2.quality_grade),
        'better_assessment': 1 if assessment1.overall_quality > assessment2.overall_quality else 2,
        'metric_comparison': {
            score1.metric.value: (score1.score, 
                                 next((s.score for s in assessment2.individual_scores 
                                      if s.metric == score1.metric), 0))
            for score1 in assessment1.individual_scores
        }
    }


def filter_high_quality_embeddings(assessments: List[EmbeddingQualityAssessment],
                                 embedding_results: List[EmbeddingResult],
                                 min_quality: float = 0.7) -> Tuple[List[EmbeddingQualityAssessment], 
                                                                   List[EmbeddingResult]]:
    """Filter embeddings by quality threshold"""
    
    filtered_assessments = []
    filtered_results = []
    
    for assessment, result in zip(assessments, embedding_results):
        if assessment.overall_quality >= min_quality:
            filtered_assessments.append(assessment)
            filtered_results.append(result)
    
    return filtered_assessments, filtered_results