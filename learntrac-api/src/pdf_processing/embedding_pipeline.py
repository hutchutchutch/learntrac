"""
Embedding Pipeline - Complete orchestrator for educational content embedding

Integrates chunking, embedding generation, and quality assessment into a unified
pipeline for processing educational documents into high-quality vector embeddings.
"""

import logging
import time
import json
import os
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from .content_chunker import ContentChunker, HybridChunkingResult, ChunkingRequest
from .embedding_generator import (
    EmbeddingGenerator, EmbeddingResult, EmbeddingConfig, 
    EmbeddingModel, BatchEmbeddingResult
)
from .embedding_quality_assessor import (
    EmbeddingQualityAssessor, EmbeddingQualityAssessment, 
    BatchQualityAssessment
)
from .chunk_metadata import ChunkMetadata, ContentType
from .structure_detector import StructureElement


class PipelineMode(Enum):
    """Pipeline processing modes"""
    STANDARD = "standard"  # Full pipeline with quality assessment
    FAST = "fast"  # Skip quality assessment for speed
    QUALITY_FOCUSED = "quality_focused"  # Emphasize quality over speed
    BATCH_OPTIMIZED = "batch_optimized"  # Optimize for large batches


class RetryStrategy(Enum):
    """Retry strategies for failed operations"""
    NONE = "none"
    SIMPLE = "simple"  # Simple retry with backoff
    ADAPTIVE = "adaptive"  # Adapt strategy based on failure type
    FALLBACK_MODEL = "fallback_model"  # Try different embedding models


@dataclass
class PipelineConfig:
    """Configuration for embedding pipeline"""
    # Chunking configuration
    chunker_config: Dict[str, Any] = field(default_factory=dict)
    
    # Embedding configuration
    embedding_config: Optional[EmbeddingConfig] = None
    fallback_embedding_config: Optional[EmbeddingConfig] = None
    
    # Quality assessment configuration
    quality_threshold: float = 0.7
    enable_quality_assessment: bool = True
    quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'educational': 0.3,
        'semantic': 0.4,
        'technical': 0.3
    })
    
    # Pipeline configuration
    mode: PipelineMode = PipelineMode.STANDARD
    retry_strategy: RetryStrategy = RetryStrategy.ADAPTIVE
    max_retries: int = 3
    parallel_processing: bool = True
    max_workers: int = 4
    
    # Caching and optimization
    enable_caching: bool = True
    cache_directory: Optional[str] = None
    batch_size: int = 10
    
    # Quality filtering
    filter_low_quality: bool = True
    min_quality_score: float = 0.6
    
    # Output configuration
    include_metadata: bool = True
    include_quality_scores: bool = True
    normalize_embeddings: bool = True


@dataclass
class DocumentInput:
    """Input document for pipeline processing"""
    document_id: str
    text: str
    title: Optional[str] = None
    subject: Optional[str] = None
    structure_elements: List[StructureElement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkEmbeddingResult:
    """Result for a single chunk embedding"""
    chunk_id: str
    chunk_text: str
    chunk_metadata: ChunkMetadata
    embedding_result: Optional[EmbeddingResult] = None
    quality_assessment: Optional[EmbeddingQualityAssessment] = None
    processing_time: float = 0.0
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class DocumentEmbeddingResult:
    """Complete embedding result for a document"""
    document_id: str
    chunk_results: List[ChunkEmbeddingResult]
    
    # Processing statistics
    total_chunks: int
    successful_embeddings: int
    failed_embeddings: int
    filtered_low_quality: int
    
    # Timing information
    chunking_time: float
    embedding_time: float
    quality_assessment_time: float
    total_processing_time: float
    
    # Quality statistics
    average_quality: float
    quality_distribution: Dict[str, int]
    
    # Pipeline metadata
    pipeline_config: PipelineConfig
    chunking_result: Optional[HybridChunkingResult] = None
    batch_quality_assessment: Optional[BatchQualityAssessment] = None
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchProcessingResult:
    """Result from batch processing multiple documents"""
    document_results: List[DocumentEmbeddingResult]
    
    # Batch statistics
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_chunks: int
    total_embeddings: int
    
    # Performance metrics
    total_processing_time: float
    average_time_per_document: float
    embeddings_per_second: float
    
    # Quality metrics
    overall_quality: float
    quality_distribution: Dict[str, int]
    
    # Resource usage
    cache_hit_rate: float
    retry_rate: float
    
    errors: List[str] = field(default_factory=list)


class EmbeddingPipeline:
    """
    Complete embedding pipeline for educational content.
    
    Orchestrates the entire process from raw text to high-quality embeddings:
    1. Content chunking with structure awareness
    2. Multi-model embedding generation with caching
    3. Comprehensive quality assessment
    4. Quality filtering and optimization
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize embedding pipeline.
        
        Args:
            config: Pipeline configuration
        """
        
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_components()
        
        # Pipeline statistics
        self.stats = {
            'documents_processed': 0,
            'chunks_processed': 0,
            'embeddings_generated': 0,
            'quality_assessments': 0,
            'cache_hits': 0,
            'retries_performed': 0,
            'total_processing_time': 0.0
        }
    
    def _initialize_components(self):
        """Initialize pipeline components"""
        
        # Initialize content chunker
        chunker_config = self.config.chunker_config
        self.chunker = ContentChunker(
            max_workers=chunker_config.get('max_workers', self.config.max_workers),
            **{k: v for k, v in chunker_config.items() if k != 'max_workers'}
        )
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(
            default_config=self.config.embedding_config,
            enable_cache=self.config.enable_caching,
            max_workers=self.config.max_workers
        )
        
        # Initialize quality assessor if enabled
        if self.config.enable_quality_assessment:
            self.quality_assessor = EmbeddingQualityAssessor(
                quality_threshold=self.config.quality_threshold,
                educational_weight=self.config.quality_weights.get('educational', 0.3),
                semantic_weight=self.config.quality_weights.get('semantic', 0.4),
                technical_weight=self.config.quality_weights.get('technical', 0.3)
            )
        else:
            self.quality_assessor = None
        
        self.logger.info(f"Embedding pipeline initialized: {self.config.mode.value} mode, "
                        f"quality_assessment={self.config.enable_quality_assessment}")
    
    def process_document(self, document: DocumentInput) -> DocumentEmbeddingResult:
        """
        Process a single document through the complete pipeline.
        
        Args:
            document: Input document to process
            
        Returns:
            DocumentEmbeddingResult with embeddings and quality assessments
        """
        
        start_time = time.time()
        
        self.logger.info(f"Processing document: {document.document_id} "
                        f"({len(document.text)} chars)")
        
        try:
            # Step 1: Chunk the document
            chunking_start = time.time()
            chunking_result = self._chunk_document(document)
            chunking_time = time.time() - chunking_start
            
            self.logger.debug(f"Chunking completed: {len(chunking_result.chunks)} chunks "
                             f"in {chunking_time:.2f}s")
            
            # Step 2: Generate embeddings for chunks
            embedding_start = time.time()
            chunk_results = self._generate_chunk_embeddings(
                chunking_result, document.document_id
            )
            embedding_time = time.time() - embedding_start
            
            self.logger.debug(f"Embedding generation completed: "
                             f"{sum(1 for r in chunk_results if r.embedding_result)} "
                             f"successful in {embedding_time:.2f}s")
            
            # Step 3: Assess quality if enabled
            quality_assessment_time = 0.0
            batch_quality_assessment = None
            
            if self.config.enable_quality_assessment and self.quality_assessor:
                quality_start = time.time()
                batch_quality_assessment = self._assess_batch_quality(chunk_results)
                quality_assessment_time = time.time() - quality_start
                
                self.logger.debug(f"Quality assessment completed in {quality_assessment_time:.2f}s")
            
            # Step 4: Filter low quality embeddings if enabled
            if self.config.filter_low_quality:
                chunk_results = self._filter_low_quality_embeddings(chunk_results)
            
            # Calculate statistics
            successful_embeddings = sum(1 for r in chunk_results if r.embedding_result)
            failed_embeddings = len(chunk_results) - successful_embeddings
            filtered_count = 0  # Would be calculated in filtering step
            
            # Calculate quality statistics
            quality_scores = [
                r.quality_assessment.overall_quality 
                for r in chunk_results 
                if r.quality_assessment
            ]
            average_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            quality_distribution = {}
            if self.quality_assessor:
                for result in chunk_results:
                    if result.quality_assessment:
                        grade = result.quality_assessment.quality_grade
                        quality_distribution[grade] = quality_distribution.get(grade, 0) + 1
            
            total_processing_time = time.time() - start_time
            
            # Create result
            result = DocumentEmbeddingResult(
                document_id=document.document_id,
                chunk_results=chunk_results,
                total_chunks=len(chunking_result.chunks),
                successful_embeddings=successful_embeddings,
                failed_embeddings=failed_embeddings,
                filtered_low_quality=filtered_count,
                chunking_time=chunking_time,
                embedding_time=embedding_time,
                quality_assessment_time=quality_assessment_time,
                total_processing_time=total_processing_time,
                average_quality=average_quality,
                quality_distribution=quality_distribution,
                pipeline_config=self.config,
                chunking_result=chunking_result,
                batch_quality_assessment=batch_quality_assessment
            )
            
            # Update statistics
            self._update_stats(result)
            
            self.logger.info(f"Document processing completed: {document.document_id} "
                           f"({successful_embeddings}/{len(chunk_results)} successful) "
                           f"in {total_processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process document {document.document_id}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Return error result
            return DocumentEmbeddingResult(
                document_id=document.document_id,
                chunk_results=[],
                total_chunks=0,
                successful_embeddings=0,
                failed_embeddings=0,
                filtered_low_quality=0,
                chunking_time=0.0,
                embedding_time=0.0,
                quality_assessment_time=0.0,
                total_processing_time=time.time() - start_time,
                average_quality=0.0,
                quality_distribution={},
                pipeline_config=self.config,
                errors=[error_msg]
            )
    
    def process_documents_batch(self, 
                               documents: List[DocumentInput],
                               max_workers: Optional[int] = None) -> BatchProcessingResult:
        """
        Process multiple documents in parallel.
        
        Args:
            documents: List of documents to process
            max_workers: Override default max workers
            
        Returns:
            BatchProcessingResult with all document results and batch statistics
        """
        
        if not documents:
            raise ValueError("Cannot process empty document list")
        
        start_time = time.time()
        max_workers = max_workers or self.config.max_workers
        
        self.logger.info(f"Processing document batch: {len(documents)} documents "
                        f"with {max_workers} workers")
        
        document_results = []
        
        if max_workers == 1 or not self.config.parallel_processing:
            # Sequential processing
            for document in documents:
                result = self.process_document(document)
                document_results.append(result)
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_document = {
                    executor.submit(self.process_document, doc): doc 
                    for doc in documents
                }
                
                # Collect results
                for future in as_completed(future_to_document):
                    try:
                        result = future.result()
                        document_results.append(result)
                    except Exception as e:
                        document = future_to_document[future]
                        error_msg = f"Failed to process document {document.document_id}: {str(e)}"
                        self.logger.error(error_msg)
                        
                        # Create error result
                        error_result = DocumentEmbeddingResult(
                            document_id=document.document_id,
                            chunk_results=[],
                            total_chunks=0,
                            successful_embeddings=0,
                            failed_embeddings=0,
                            filtered_low_quality=0,
                            chunking_time=0.0,
                            embedding_time=0.0,
                            quality_assessment_time=0.0,
                            total_processing_time=0.0,
                            average_quality=0.0,
                            quality_distribution={},
                            pipeline_config=self.config,
                            errors=[error_msg]
                        )
                        document_results.append(error_result)
        
        # Calculate batch statistics
        total_processing_time = time.time() - start_time
        
        successful_documents = sum(1 for r in document_results if not r.errors)
        failed_documents = len(document_results) - successful_documents
        total_chunks = sum(r.total_chunks for r in document_results)
        total_embeddings = sum(r.successful_embeddings for r in document_results)
        
        # Quality statistics
        all_quality_scores = []
        quality_distribution = {}
        
        for result in document_results:
            if result.average_quality > 0:
                all_quality_scores.append(result.average_quality)
            
            for grade, count in result.quality_distribution.items():
                quality_distribution[grade] = quality_distribution.get(grade, 0) + count
        
        overall_quality = sum(all_quality_scores) / len(all_quality_scores) if all_quality_scores else 0.0
        
        # Performance metrics
        average_time_per_document = total_processing_time / max(len(documents), 1)
        embeddings_per_second = total_embeddings / max(total_processing_time, 0.001)
        
        # Cache and retry metrics
        cache_hit_rate = 0.0  # Would be calculated from embedding generator stats
        retry_rate = sum(
            sum(r.retry_count for r in doc_result.chunk_results)
            for doc_result in document_results
        ) / max(total_chunks, 1)
        
        batch_result = BatchProcessingResult(
            document_results=document_results,
            total_documents=len(documents),
            successful_documents=successful_documents,
            failed_documents=failed_documents,
            total_chunks=total_chunks,
            total_embeddings=total_embeddings,
            total_processing_time=total_processing_time,
            average_time_per_document=average_time_per_document,
            embeddings_per_second=embeddings_per_second,
            overall_quality=overall_quality,
            quality_distribution=quality_distribution,
            cache_hit_rate=cache_hit_rate,
            retry_rate=retry_rate
        )
        
        self.logger.info(f"Batch processing completed: {successful_documents}/{len(documents)} "
                        f"successful documents, {total_embeddings} embeddings "
                        f"in {total_processing_time:.2f}s")
        
        return batch_result
    
    def _chunk_document(self, document: DocumentInput) -> HybridChunkingResult:
        """Chunk document using content chunker"""
        
        metadata_base = {
            'title': document.title or '',
            'subject': document.subject or '',
            **document.metadata
        }
        
        return self.chunker.chunk_content(
            text=document.text,
            book_id=document.document_id,
            structure_elements=document.structure_elements,
            metadata_base=metadata_base
        )
    
    def _generate_chunk_embeddings(self,
                                 chunking_result: HybridChunkingResult,
                                 document_id: str) -> List[ChunkEmbeddingResult]:
        """Generate embeddings for all chunks"""
        
        chunk_results = []
        
        for i, (chunk_text, chunk_metadata) in enumerate(
            zip(chunking_result.chunks, chunking_result.metadata_list)
        ):
            chunk_id = f"{document_id}_chunk_{i}"
            
            chunk_result = ChunkEmbeddingResult(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                chunk_metadata=chunk_metadata
            )
            
            # Generate embedding with retry logic
            embedding_result = self._generate_embedding_with_retry(
                chunk_text, chunk_result
            )
            
            if embedding_result:
                chunk_result.embedding_result = embedding_result
            else:
                chunk_result.error = "Failed to generate embedding after retries"
            
            chunk_results.append(chunk_result)
        
        return chunk_results
    
    def _generate_embedding_with_retry(self,
                                     text: str,
                                     chunk_result: ChunkEmbeddingResult) -> Optional[EmbeddingResult]:
        """Generate embedding with retry logic"""
        
        last_error = None
        config = self.config.embedding_config
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                # Try main config first, then fallback config
                if attempt == 0:
                    embedding_config = config
                elif self.config.fallback_embedding_config:
                    embedding_config = self.config.fallback_embedding_config
                else:
                    embedding_config = config
                
                result = self.embedding_generator.generate_embedding(text, embedding_config)
                chunk_result.processing_time = time.time() - start_time
                chunk_result.retry_count = attempt
                
                return result
                
            except Exception as e:
                last_error = e
                chunk_result.retry_count = attempt + 1
                
                if attempt < self.config.max_retries:
                    self.logger.warning(f"Embedding generation failed (attempt {attempt + 1}): {e}")
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"Embedding generation failed after {self.config.max_retries + 1} attempts: {e}")
        
        chunk_result.error = str(last_error)
        return None
    
    def _assess_batch_quality(self, 
                            chunk_results: List[ChunkEmbeddingResult]) -> Optional[BatchQualityAssessment]:
        """Assess quality for all chunk embeddings"""
        
        if not self.quality_assessor:
            return None
        
        # Collect successful embeddings
        embedding_results = []
        chunk_metadata_list = []
        
        for chunk_result in chunk_results:
            if chunk_result.embedding_result:
                embedding_results.append(chunk_result.embedding_result)
                chunk_metadata_list.append(chunk_result.chunk_metadata)
        
        if not embedding_results:
            return None
        
        # Assess batch quality
        batch_assessment = self.quality_assessor.assess_batch_quality(
            embedding_results, chunk_metadata_list
        )
        
        # Update individual chunk results with quality assessments
        assessment_idx = 0
        for chunk_result in chunk_results:
            if chunk_result.embedding_result:
                if assessment_idx < len(batch_assessment.individual_assessments):
                    chunk_result.quality_assessment = batch_assessment.individual_assessments[assessment_idx]
                    assessment_idx += 1
        
        return batch_assessment
    
    def _filter_low_quality_embeddings(self, 
                                     chunk_results: List[ChunkEmbeddingResult]) -> List[ChunkEmbeddingResult]:
        """Filter out low quality embeddings"""
        
        if not self.config.filter_low_quality:
            return chunk_results
        
        filtered_results = []
        
        for chunk_result in chunk_results:
            if chunk_result.quality_assessment:
                if chunk_result.quality_assessment.overall_quality >= self.config.min_quality_score:
                    filtered_results.append(chunk_result)
                else:
                    self.logger.debug(f"Filtered low quality embedding: "
                                    f"{chunk_result.chunk_id} "
                                    f"(quality: {chunk_result.quality_assessment.overall_quality:.2f})")
            else:
                # Keep embeddings without quality assessment
                filtered_results.append(chunk_result)
        
        return filtered_results
    
    def _update_stats(self, result: DocumentEmbeddingResult):
        """Update pipeline statistics"""
        
        self.stats['documents_processed'] += 1
        self.stats['chunks_processed'] += result.total_chunks
        self.stats['embeddings_generated'] += result.successful_embeddings
        self.stats['total_processing_time'] += result.total_processing_time
        
        if result.batch_quality_assessment:
            self.stats['quality_assessments'] += len(result.batch_quality_assessment.individual_assessments)
        
        # Update retry statistics
        total_retries = sum(r.retry_count for r in result.chunk_results)
        self.stats['retries_performed'] += total_retries
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['documents_processed'] > 0:
            stats['avg_chunks_per_document'] = stats['chunks_processed'] / stats['documents_processed']
            stats['avg_processing_time_per_document'] = stats['total_processing_time'] / stats['documents_processed']
        
        if stats['chunks_processed'] > 0:
            stats['embedding_success_rate'] = stats['embeddings_generated'] / stats['chunks_processed']
            stats['retry_rate'] = stats['retries_performed'] / stats['chunks_processed']
        
        if stats['total_processing_time'] > 0:
            stats['embeddings_per_second'] = stats['embeddings_generated'] / stats['total_processing_time']
        
        # Add component statistics
        stats['chunker_statistics'] = self.chunker.get_processing_statistics()
        stats['embedding_generator_statistics'] = self.embedding_generator.get_statistics()
        
        if self.quality_assessor:
            stats['quality_assessor_statistics'] = self.quality_assessor.get_assessment_statistics()
        
        return stats
    
    def reset_statistics(self):
        """Reset all pipeline statistics"""
        
        self.stats = {
            'documents_processed': 0,
            'chunks_processed': 0,
            'embeddings_generated': 0,
            'quality_assessments': 0,
            'cache_hits': 0,
            'retries_performed': 0,
            'total_processing_time': 0.0
        }
        
        # Reset component statistics
        self.chunker.reset_statistics()
        self.embedding_generator.reset_statistics()
        
        if self.quality_assessor:
            self.quality_assessor.reset_statistics()
    
    def export_embeddings(self, 
                         result: DocumentEmbeddingResult,
                         format: str = 'numpy',
                         output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export embeddings in various formats.
        
        Args:
            result: Document embedding result to export
            format: Export format ('numpy', 'json', 'csv', 'parquet')
            output_path: Optional output file path
            
        Returns:
            Export metadata and statistics
        """
        
        # Collect embeddings and metadata
        embeddings = []
        metadata_list = []
        
        for chunk_result in result.chunk_results:
            if chunk_result.embedding_result:
                embeddings.append(chunk_result.embedding_result.embedding)
                
                export_metadata = {
                    'chunk_id': chunk_result.chunk_id,
                    'text': chunk_result.chunk_text,
                    'content_type': chunk_result.chunk_metadata.content_type.value,
                    'difficulty': chunk_result.chunk_metadata.difficulty,
                    'confidence': chunk_result.chunk_metadata.confidence_score,
                    'chapter': chunk_result.chunk_metadata.chapter,
                    'section': chunk_result.chunk_metadata.section,
                    'embedding_model': chunk_result.embedding_result.model.value,
                    'generation_time': chunk_result.embedding_result.generation_time
                }
                
                if chunk_result.quality_assessment:
                    export_metadata.update({
                        'quality_score': chunk_result.quality_assessment.overall_quality,
                        'quality_grade': chunk_result.quality_assessment.quality_grade
                    })
                
                metadata_list.append(export_metadata)
        
        if not embeddings:
            raise ValueError("No embeddings to export")
        
        embeddings_array = np.array(embeddings)
        
        export_info = {
            'document_id': result.document_id,
            'total_embeddings': len(embeddings),
            'embedding_dimensions': embeddings_array.shape[1] if embeddings_array.size > 0 else 0,
            'export_format': format,
            'export_timestamp': time.time()
        }
        
        if output_path:
            if format == 'numpy':
                np.savez(output_path, 
                        embeddings=embeddings_array, 
                        metadata=metadata_list,
                        export_info=export_info)
            elif format == 'json':
                export_data = {
                    'embeddings': embeddings_array.tolist(),
                    'metadata': metadata_list,
                    'export_info': export_info
                }
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            export_info['output_path'] = output_path
            self.logger.info(f"Exported {len(embeddings)} embeddings to {output_path}")
        
        return export_info
    
    def update_config(self, new_config: PipelineConfig):
        """Update pipeline configuration and reinitialize components"""
        
        self.config = new_config
        self._initialize_components()
        self.logger.info("Pipeline configuration updated and components reinitialized")


# Utility functions for pipeline configuration

def create_fast_pipeline_config() -> PipelineConfig:
    """Create configuration optimized for speed"""
    
    from .embedding_generator import create_educational_config, EmbeddingModel
    
    return PipelineConfig(
        mode=PipelineMode.FAST,
        embedding_config=create_educational_config(EmbeddingModel.SENTENCE_TRANSFORMERS_MINILM),
        enable_quality_assessment=False,
        parallel_processing=True,
        max_workers=8,
        batch_size=20,
        filter_low_quality=False
    )


def create_quality_focused_config() -> PipelineConfig:
    """Create configuration optimized for quality"""
    
    from .embedding_generator import create_educational_config, EmbeddingModel
    
    return PipelineConfig(
        mode=PipelineMode.QUALITY_FOCUSED,
        embedding_config=create_educational_config(EmbeddingModel.OPENAI_3_LARGE),
        fallback_embedding_config=create_educational_config(EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET),
        enable_quality_assessment=True,
        quality_threshold=0.8,
        parallel_processing=True,
        max_workers=4,
        batch_size=8,
        filter_low_quality=True,
        min_quality_score=0.7,
        max_retries=5,
        retry_strategy=RetryStrategy.ADAPTIVE
    )


def create_batch_optimized_config() -> PipelineConfig:
    """Create configuration optimized for large batches"""
    
    from .embedding_generator import create_educational_config, EmbeddingModel
    
    return PipelineConfig(
        mode=PipelineMode.BATCH_OPTIMIZED,
        embedding_config=create_educational_config(EmbeddingModel.SENTENCE_TRANSFORMERS_MPNET),
        enable_quality_assessment=True,
        quality_threshold=0.7,
        parallel_processing=True,
        max_workers=12,
        batch_size=50,
        enable_caching=True,
        filter_low_quality=True
    )