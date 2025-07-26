"""
Content Chunker - Main hybrid chunking controller

Orchestrates intelligent content chunking by selecting between content-aware
and fallback strategies based on document structure quality assessment.
"""

import logging
import time
import threading
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from .chunk_metadata import ChunkMetadata, ContentType
from .structure_quality_assessor import StructureQualityAssessor, QualityAssessment, ChunkingStrategy
from .content_aware_chunker import ContentAwareChunker, ChunkingResult as ContentAwareResult
from .fallback_chunker import FallbackChunker, FallbackChunkingResult
from .structure_detector import DetectionResult, StructureElement


class ChunkingMode(Enum):
    """Chunking operation modes"""
    SINGLE = "single"  # Process one document
    BATCH = "batch"    # Process multiple documents
    STREAMING = "streaming"  # Process documents as they arrive


@dataclass
class ChunkingRequest:
    """Request for chunking operation"""
    text: str
    book_id: str
    metadata_base: Dict[str, Any] = field(default_factory=dict)
    structure_elements: List[StructureElement] = field(default_factory=list)
    force_strategy: Optional[ChunkingStrategy] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class HybridChunkingResult:
    """Complete result from hybrid chunking operation"""
    chunks: List[str]
    metadata_list: List[ChunkMetadata]
    
    # Strategy and quality information
    strategy_used: ChunkingStrategy
    quality_assessment: Optional[QualityAssessment]
    
    # Performance metrics
    processing_time: float
    chunks_per_second: float
    
    # Statistics and diagnostics
    chunking_statistics: Dict[str, Any]
    warnings: List[str]
    recommendations: List[str]
    
    # Original component results (for debugging)
    content_aware_result: Optional[ContentAwareResult] = None
    fallback_result: Optional[FallbackChunkingResult] = None


@dataclass
class BatchChunkingResult:
    """Result from batch chunking operation"""
    results: List[HybridChunkingResult]
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_processing_time: float
    average_chunks_per_document: float
    batch_statistics: Dict[str, Any]
    errors: List[str]


class ContentChunker:
    """
    Main hybrid content chunker controller.
    
    Orchestrates intelligent content chunking by:
    1. Assessing document structure quality
    2. Selecting optimal chunking strategy
    3. Delegating to appropriate chunker
    4. Post-processing and validation
    5. Providing comprehensive results and metrics
    """
    
    def __init__(self,
                 # Structure assessment settings
                 structure_quality_threshold: float = 0.3,
                 min_chapters_for_structure: int = 2,
                 
                 # Content-aware chunker settings
                 content_aware_target_size: int = 1250,
                 content_aware_min_size: int = 300,
                 content_aware_max_size: int = 1500,
                 content_aware_overlap: int = 150,
                 
                 # Fallback chunker settings
                 fallback_target_size: int = 1000,
                 fallback_min_size: int = 300,
                 fallback_max_size: int = 1500,
                 fallback_overlap: int = 200,
                 
                 # Processing settings
                 enable_preprocessing: bool = True,
                 enable_postprocessing: bool = True,
                 thread_safe: bool = True,
                 max_workers: int = 4):
        """
        Initialize hybrid content chunker.
        
        Args:
            structure_quality_threshold: Threshold for strategy selection
            min_chapters_for_structure: Minimum chapters for structured approach
            content_aware_*: Settings for content-aware chunker
            fallback_*: Settings for fallback chunker
            enable_preprocessing: Enable text preprocessing
            enable_postprocessing: Enable chunk validation and enhancement
            thread_safe: Enable thread-safe operations
            max_workers: Maximum threads for batch processing
        """
        
        self.structure_quality_threshold = structure_quality_threshold
        self.enable_preprocessing = enable_preprocessing
        self.enable_postprocessing = enable_postprocessing
        self.thread_safe = thread_safe
        self.max_workers = max_workers
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_components(
            structure_quality_threshold, min_chapters_for_structure,
            content_aware_target_size, content_aware_min_size, content_aware_max_size, content_aware_overlap,
            fallback_target_size, fallback_min_size, fallback_max_size, fallback_overlap
        )
        
        # Thread safety
        self._lock = threading.RLock() if thread_safe else None
        
        # Performance tracking
        self.processing_stats = {
            'total_documents': 0,
            'content_aware_used': 0,
            'fallback_used': 0,
            'hybrid_used': 0,
            'total_chunks_created': 0,
            'total_processing_time': 0.0
        }
    
    def _initialize_components(self, *args):
        """Initialize chunking components"""
        (structure_threshold, min_chapters,
         ca_target, ca_min, ca_max, ca_overlap,
         fb_target, fb_min, fb_max, fb_overlap) = args
        
        # Structure quality assessor
        self.quality_assessor = StructureQualityAssessor(
            strategy_threshold=structure_threshold,
            min_chapters_for_structure=min_chapters
        )
        
        # Content-aware chunker
        self.content_aware_chunker = ContentAwareChunker(
            target_chunk_size=ca_target,
            min_chunk_size=ca_min,
            max_chunk_size=ca_max,
            overlap_size=ca_overlap,
            preserve_math=True,
            preserve_definitions=True,
            preserve_examples=True
        )
        
        # Fallback chunker
        self.fallback_chunker = FallbackChunker(
            target_chunk_size=fb_target,
            min_chunk_size=fb_min,
            max_chunk_size=fb_max,
            overlap_size=fb_overlap,
            prefer_sentence_boundaries=True,
            preserve_paragraphs=True
        )
    
    def chunk_content(self, 
                     text: str,
                     book_id: str,
                     structure_elements: List[StructureElement] = None,
                     metadata_base: Dict[str, Any] = None,
                     force_strategy: Optional[ChunkingStrategy] = None) -> HybridChunkingResult:
        """
        Chunk content using hybrid strategy selection.
        
        Args:
            text: Text content to chunk
            book_id: Unique identifier for the book
            structure_elements: Detected structure elements
            metadata_base: Base metadata to include in chunks
            force_strategy: Force specific strategy (for testing/debugging)
            
        Returns:
            HybridChunkingResult with chunks, metadata, and diagnostics
        """
        start_time = time.time()
        
        if self.thread_safe and self._lock:
            with self._lock:
                return self._chunk_content_internal(
                    text, book_id, structure_elements, metadata_base, force_strategy, start_time
                )
        else:
            return self._chunk_content_internal(
                text, book_id, structure_elements, metadata_base, force_strategy, start_time
            )
    
    def _chunk_content_internal(self,
                               text: str,
                               book_id: str,
                               structure_elements: List[StructureElement],
                               metadata_base: Dict[str, Any],
                               force_strategy: Optional[ChunkingStrategy],
                               start_time: float) -> HybridChunkingResult:
        """Internal chunking implementation"""
        
        self.logger.info(f"Starting hybrid chunking for {book_id}: {len(text)} characters")
        
        # Validate inputs
        if not text.strip():
            return self._create_empty_result(book_id, "Empty text provided", start_time)
        
        structure_elements = structure_elements or []
        metadata_base = metadata_base or {}
        
        # Preprocessing
        if self.enable_preprocessing:
            text = self._preprocess_text(text)
        
        # Assess structure quality (unless strategy is forced)
        quality_assessment = None
        if force_strategy:
            strategy = force_strategy
            self.logger.info(f"Using forced strategy: {strategy.value}")
        else:
            quality_assessment = self._assess_structure_quality(structure_elements)
            strategy = quality_assessment.recommended_strategy
            self.logger.info(f"Selected strategy: {strategy.value} (quality: {quality_assessment.overall_quality_score:.2f})")
        
        # Execute chunking strategy
        chunks, metadata_list, component_result = self._execute_chunking_strategy(
            strategy, text, book_id, structure_elements, metadata_base
        )
        
        # Post-processing
        if self.enable_postprocessing:
            chunks, metadata_list = self._postprocess_chunks(chunks, metadata_list, book_id)
        
        # Calculate performance metrics
        end_time = time.time()
        processing_time = end_time - start_time
        chunks_per_second = len(chunks) / max(processing_time, 0.001)
        
        # Generate statistics and diagnostics
        statistics = self._calculate_hybrid_statistics(chunks, metadata_list, strategy, quality_assessment)
        warnings = self._generate_warnings(chunks, metadata_list, quality_assessment)
        recommendations = self._generate_recommendations(quality_assessment, statistics)
        
        # Update global statistics
        self._update_processing_stats(strategy, len(chunks), processing_time)
        
        # Create result
        result = HybridChunkingResult(
            chunks=chunks,
            metadata_list=metadata_list,
            strategy_used=strategy,
            quality_assessment=quality_assessment,
            processing_time=processing_time,
            chunks_per_second=chunks_per_second,
            chunking_statistics=statistics,
            warnings=warnings,
            recommendations=recommendations
        )
        
        # Store component results for debugging
        if isinstance(component_result, ContentAwareResult):
            result.content_aware_result = component_result
        elif isinstance(component_result, FallbackChunkingResult):
            result.fallback_result = component_result
        
        self.logger.info(f"Hybrid chunking complete: {len(chunks)} chunks in {processing_time:.2f}s")
        return result
    
    def chunk_batch(self, 
                   requests: List[ChunkingRequest],
                   max_workers: Optional[int] = None) -> BatchChunkingResult:
        """
        Process multiple chunking requests in parallel.
        
        Args:
            requests: List of chunking requests
            max_workers: Override default max workers
            
        Returns:
            BatchChunkingResult with aggregated results
        """
        start_time = time.time()
        max_workers = max_workers or self.max_workers
        
        self.logger.info(f"Starting batch chunking: {len(requests)} documents with {max_workers} workers")
        
        results = []
        errors = []
        
        if max_workers == 1:
            # Sequential processing
            for request in requests:
                try:
                    result = self.chunk_content(
                        text=request.text,
                        book_id=request.book_id,
                        structure_elements=request.structure_elements,
                        metadata_base=request.metadata_base,
                        force_strategy=request.force_strategy
                    )
                    results.append(result)
                except Exception as e:
                    error_msg = f"Failed to process {request.book_id}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg, exc_info=True)
        else:
            # Parallel processing
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_request = {}
                for request in requests:
                    future = executor.submit(
                        self.chunk_content,
                        request.text,
                        request.book_id,
                        request.structure_elements,
                        request.metadata_base,
                        request.force_strategy
                    )
                    future_to_request[future] = request
                
                # Collect results
                for future in as_completed(future_to_request):
                    request = future_to_request[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        error_msg = f"Failed to process {request.book_id}: {str(e)}"
                        errors.append(error_msg)
                        self.logger.error(error_msg, exc_info=True)
        
        # Calculate batch statistics
        end_time = time.time()
        total_processing_time = end_time - start_time
        successful_documents = len(results)
        failed_documents = len(errors)
        
        avg_chunks_per_doc = (sum(len(r.chunks) for r in results) / max(successful_documents, 1))
        
        batch_stats = self._calculate_batch_statistics(results, total_processing_time)
        
        self.logger.info(f"Batch chunking complete: {successful_documents}/{len(requests)} successful in {total_processing_time:.2f}s")
        
        return BatchChunkingResult(
            results=results,
            total_documents=len(requests),
            successful_documents=successful_documents,
            failed_documents=failed_documents,
            total_processing_time=total_processing_time,
            average_chunks_per_document=avg_chunks_per_doc,
            batch_statistics=batch_stats,
            errors=errors
        )
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before chunking"""
        # Basic text cleaning and normalization
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove common PDF artifacts
        text = re.sub(r'^Page \d+.*?\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n.*?Page \d+.*?$', '', text, flags=re.MULTILINE)
        
        # Remove excessive dashes/underscores (formatting artifacts)
        text = re.sub(r'^[-_]{5,}.*?$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _assess_structure_quality(self, structure_elements: List[StructureElement]) -> QualityAssessment:
        """Assess structure quality for strategy selection"""
        if not structure_elements:
            # Create minimal detection result for assessment
            from .structure_detector import StructureHierarchy, DetectionResult
            
            empty_hierarchy = StructureHierarchy(
                elements=[],
                total_chapters=0,
                total_sections=0,
                max_depth=0,
                numbering_consistency=0.0,
                overall_confidence=0.0,
                quality_score=0.0
            )
            
            empty_detection = DetectionResult(
                hierarchy=empty_hierarchy,
                is_valid_textbook=False,
                warnings=["No structure elements provided"],
                statistics={}
            )
            
            return self.quality_assessor.assess_structure_quality(empty_detection)
        
        # Create detection result from structure elements
        from .structure_detector import StructureHierarchy, DetectionResult
        
        # Calculate basic hierarchy metrics
        chapters = [e for e in structure_elements if e.type.value == 'chapter']
        sections = [e for e in structure_elements if e.type.value == 'section']
        max_depth = max([e.level for e in structure_elements], default=0)
        
        # Estimate numbering consistency
        numbering_consistency = self._estimate_numbering_consistency(structure_elements)
        
        hierarchy = StructureHierarchy(
            elements=structure_elements,
            total_chapters=len(chapters),
            total_sections=len(sections),
            max_depth=max_depth,
            numbering_consistency=numbering_consistency,
            overall_confidence=0.8,  # Assume good confidence if elements provided
            quality_score=0.7  # Default reasonable quality
        )
        
        detection_result = DetectionResult(
            hierarchy=hierarchy,
            is_valid_textbook=len(chapters) >= 2,
            warnings=[],
            statistics={}
        )
        
        return self.quality_assessor.assess_structure_quality(detection_result)
    
    def _estimate_numbering_consistency(self, elements: List[StructureElement]) -> float:
        """Estimate numbering consistency from structure elements"""
        if not elements:
            return 0.0
        
        # Group by type and level
        groups = {}
        for element in elements:
            key = (element.type, element.level)
            groups.setdefault(key, []).append(element)
        
        consistency_scores = []
        
        for group in groups.values():
            if len(group) < 2:
                consistency_scores.append(1.0)
                continue
            
            # Check numbering style consistency
            styles = set()
            for element in group:
                if hasattr(element, 'numbering_style') and element.numbering_style:
                    styles.add(element.numbering_style)
            
            if len(styles) <= 1:
                consistency_scores.append(1.0)
            else:
                consistency_scores.append(1.0 / len(styles))
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    def _execute_chunking_strategy(self,
                                 strategy: ChunkingStrategy,
                                 text: str,
                                 book_id: str,
                                 structure_elements: List[StructureElement],
                                 metadata_base: Dict[str, Any]) -> tuple:
        """Execute the selected chunking strategy"""
        
        if strategy == ChunkingStrategy.CONTENT_AWARE:
            result = self.content_aware_chunker.chunk_content(
                text=text,
                structure_elements=structure_elements,
                book_id=book_id,
                metadata_base=metadata_base
            )
            return result.chunks, result.metadata_list, result
        
        elif strategy == ChunkingStrategy.FALLBACK:
            result = self.fallback_chunker.chunk_content(
                text=text,
                book_id=book_id,
                metadata_base=metadata_base
            )
            return result.chunks, result.metadata_list, result
        
        elif strategy == ChunkingStrategy.HYBRID:
            # Use both strategies and merge results intelligently
            return self._execute_hybrid_strategy(text, book_id, structure_elements, metadata_base)
        
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")
    
    def _execute_hybrid_strategy(self,
                               text: str,
                               book_id: str,
                               structure_elements: List[StructureElement],
                               metadata_base: Dict[str, Any]) -> tuple:
        """Execute hybrid strategy combining both approaches"""
        
        # Try content-aware first
        try:
            ca_result = self.content_aware_chunker.chunk_content(
                text=text,
                structure_elements=structure_elements,
                book_id=book_id,
                metadata_base=metadata_base
            )
            
            # If content-aware produces reasonable results, use it
            if (len(ca_result.chunks) > 0 and 
                ca_result.chunking_statistics.get('avg_confidence', 0) > 0.6):
                return ca_result.chunks, ca_result.metadata_list, ca_result
        
        except Exception as e:
            self.logger.warning(f"Content-aware chunking failed: {e}")
        
        # Fall back to fallback chunker
        fb_result = self.fallback_chunker.chunk_content(
            text=text,
            book_id=book_id,
            metadata_base=metadata_base
        )
        
        return fb_result.chunks, fb_result.metadata_list, fb_result
    
    def _postprocess_chunks(self,
                          chunks: List[str],
                          metadata_list: List[ChunkMetadata],
                          book_id: str) -> tuple:
        """Post-process chunks for quality and consistency"""
        
        processed_chunks = []
        processed_metadata = []
        
        for i, (chunk, metadata) in enumerate(zip(chunks, metadata_list)):
            # Validate chunk quality
            if self._validate_chunk_quality(chunk, metadata):
                processed_chunks.append(chunk)
                processed_metadata.append(metadata)
            else:
                # Try to merge with adjacent chunks or skip
                self.logger.warning(f"Chunk {i} failed quality validation and was skipped")
        
        # Update chunk IDs to be sequential after processing
        for i, metadata in enumerate(processed_metadata):
            metadata.chunk_id = f"{book_id}_chunk_{i:04d}"
        
        return processed_chunks, processed_metadata
    
    def _validate_chunk_quality(self, chunk: str, metadata: ChunkMetadata) -> bool:
        """Validate individual chunk quality"""
        
        # Check minimum length
        if len(chunk.strip()) < 50:
            return False
        
        # Check confidence threshold
        if metadata.confidence_score < 0.2:
            return False
        
        # Check for reasonable word count
        word_count = len(chunk.split())
        if word_count < 5:
            return False
        
        # Check for excessive repetition
        words = chunk.lower().split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Too repetitive
                return False
        
        return True
    
    def _calculate_hybrid_statistics(self,
                                   chunks: List[str],
                                   metadata_list: List[ChunkMetadata],
                                   strategy: ChunkingStrategy,
                                   quality_assessment: Optional[QualityAssessment]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for hybrid chunking"""
        
        if not chunks:
            return {'total_chunks': 0}
        
        chunk_sizes = [len(chunk) for chunk in chunks]
        
        # Content type distribution
        content_types = {}
        difficulties = []
        confidences = []
        
        for metadata in metadata_list:
            content_type = metadata.content_type.value
            content_types[content_type] = content_types.get(content_type, 0) + 1
            difficulties.append(metadata.difficulty)
            confidences.append(metadata.confidence_score)
        
        # Advanced statistics
        statistics = {
            # Basic metrics
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'median_chunk_size': sorted(chunk_sizes)[len(chunk_sizes) // 2],
            'chunk_size_std_dev': (sum((s - sum(chunk_sizes) / len(chunk_sizes)) ** 2 for s in chunk_sizes) / len(chunk_sizes)) ** 0.5,
            
            # Content analysis
            'total_characters': sum(chunk_sizes),
            'total_words': sum(len(chunk.split()) for chunk in chunks),
            'avg_words_per_chunk': sum(len(chunk.split()) for chunk in chunks) / len(chunks),
            'content_type_distribution': content_types,
            
            # Quality metrics
            'avg_difficulty': sum(difficulties) / len(difficulties) if difficulties else 0,
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            
            # Strategy information
            'chunking_strategy': strategy.value,
            'structure_quality_score': quality_assessment.overall_quality_score if quality_assessment else 0,
            
            # Size distribution analysis
            'size_quartiles': self._calculate_quartiles(chunk_sizes),
            'chunks_within_target': sum(1 for size in chunk_sizes if 800 <= size <= 1600) / len(chunk_sizes),
            
            # Educational content analysis
            'math_content_chunks': content_types.get('math', 0),
            'definition_chunks': content_types.get('definition', 0),
            'example_chunks': content_types.get('example', 0),
            'text_chunks': content_types.get('text', 0)
        }
        
        return statistics
    
    def _calculate_quartiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate quartiles for a list of values"""
        if not values:
            return {'q1': 0, 'q2': 0, 'q3': 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'q1': sorted_values[n // 4],
            'q2': sorted_values[n // 2],  # median
            'q3': sorted_values[3 * n // 4]
        }
    
    def _generate_warnings(self,
                         chunks: List[str],
                         metadata_list: List[ChunkMetadata],
                         quality_assessment: Optional[QualityAssessment]) -> List[str]:
        """Generate warnings about chunking quality"""
        warnings = []
        
        if not chunks:
            warnings.append("No chunks were created from the input text")
            return warnings
        
        # Size-related warnings
        chunk_sizes = [len(chunk) for chunk in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)
        
        if avg_size < 500:
            warnings.append(f"Average chunk size ({avg_size:.0f}) is quite small - may affect retrieval quality")
        elif avg_size > 2000:
            warnings.append(f"Average chunk size ({avg_size:.0f}) is quite large - may affect processing speed")
        
        # Confidence warnings
        avg_confidence = sum(m.confidence_score for m in metadata_list) / len(metadata_list)
        if avg_confidence < 0.5:
            warnings.append(f"Low average confidence ({avg_confidence:.2f}) - consider manual review")
        
        low_confidence_chunks = sum(1 for m in metadata_list if m.confidence_score < 0.4)
        if low_confidence_chunks > len(chunks) * 0.3:
            warnings.append(f"{low_confidence_chunks} chunks have low confidence scores")
        
        # Structure quality warnings
        if quality_assessment and quality_assessment.overall_quality_score < 0.4:
            warnings.append("Poor document structure detected - chunking quality may be suboptimal")
        
        # Content distribution warnings
        content_types = {}
        for metadata in metadata_list:
            content_type = metadata.content_type.value
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        if content_types.get('text', 0) == len(chunks):
            warnings.append("No specialized content types detected - all chunks classified as general text")
        
        # Size variance warning
        size_std_dev = (sum((s - avg_size) ** 2 for s in chunk_sizes) / len(chunk_sizes)) ** 0.5
        if size_std_dev > avg_size * 0.5:
            warnings.append("High variance in chunk sizes - document may have inconsistent content density")
        
        return warnings
    
    def _generate_recommendations(self,
                                quality_assessment: Optional[QualityAssessment],
                                statistics: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving chunking"""
        recommendations = []
        
        # Strategy recommendations
        if quality_assessment:
            if quality_assessment.overall_quality_score > 0.7:
                recommendations.append("High structure quality - consider using content-aware chunking exclusively")
            elif quality_assessment.overall_quality_score < 0.3:
                recommendations.append("Poor structure quality - consider document restructuring before processing")
        
        # Size recommendations
        avg_size = statistics.get('avg_chunk_size', 0)
        if avg_size < 800:
            recommendations.append("Consider increasing target chunk size for better context preservation")
        elif avg_size > 1600:
            recommendations.append("Consider decreasing target chunk size for faster processing")
        
        # Confidence recommendations
        avg_confidence = statistics.get('avg_confidence', 0)
        if avg_confidence < 0.6:
            recommendations.append("Low confidence scores suggest manual review of chunking results")
        
        # Content type recommendations
        content_dist = statistics.get('content_type_distribution', {})
        total_chunks = statistics.get('total_chunks', 0)
        
        if content_dist.get('math', 0) > total_chunks * 0.3:
            recommendations.append("High mathematical content - consider specialized mathematical processing")
        
        if content_dist.get('definition', 0) == 0 and total_chunks > 10:
            recommendations.append("No definitions detected - may benefit from enhanced definition detection")
        
        # Performance recommendations
        chunks_within_target = statistics.get('chunks_within_target', 0)
        if chunks_within_target < 0.7:
            recommendations.append("Many chunks outside target size range - consider adjusting chunking parameters")
        
        return recommendations
    
    def _update_processing_stats(self, strategy: ChunkingStrategy, chunk_count: int, processing_time: float):
        """Update global processing statistics"""
        self.processing_stats['total_documents'] += 1
        self.processing_stats['total_chunks_created'] += chunk_count
        self.processing_stats['total_processing_time'] += processing_time
        
        if strategy == ChunkingStrategy.CONTENT_AWARE:
            self.processing_stats['content_aware_used'] += 1
        elif strategy == ChunkingStrategy.FALLBACK:
            self.processing_stats['fallback_used'] += 1
        elif strategy == ChunkingStrategy.HYBRID:
            self.processing_stats['hybrid_used'] += 1
    
    def _calculate_batch_statistics(self, results: List[HybridChunkingResult], total_time: float) -> Dict[str, Any]:
        """Calculate statistics for batch processing"""
        if not results:
            return {}
        
        # Strategy distribution
        strategy_counts = {}
        for result in results:
            strategy = result.strategy_used.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # Performance metrics
        total_chunks = sum(len(r.chunks) for r in results)
        avg_processing_time = sum(r.processing_time for r in results) / len(results)
        total_characters = sum(r.chunking_statistics.get('total_characters', 0) for r in results)
        
        # Quality metrics
        avg_quality_scores = []
        for result in results:
            if result.quality_assessment:
                avg_quality_scores.append(result.quality_assessment.overall_quality_score)
        
        avg_quality = sum(avg_quality_scores) / len(avg_quality_scores) if avg_quality_scores else 0
        
        return {
            'strategy_distribution': strategy_counts,
            'total_chunks_created': total_chunks,
            'total_characters_processed': total_characters,
            'avg_processing_time_per_doc': avg_processing_time,
            'avg_chunks_per_doc': total_chunks / len(results),
            'avg_structure_quality': avg_quality,
            'throughput_docs_per_second': len(results) / max(total_time, 0.001),
            'throughput_chunks_per_second': total_chunks / max(total_time, 0.001),
            'parallel_efficiency': (avg_processing_time * len(results)) / max(total_time, 0.001)
        }
    
    def _create_empty_result(self, book_id: str, reason: str, start_time: float) -> HybridChunkingResult:
        """Create empty result for error cases"""
        
        processing_time = time.time() - start_time
        
        return HybridChunkingResult(
            chunks=[],
            metadata_list=[],
            strategy_used=ChunkingStrategy.FALLBACK,  # Default
            quality_assessment=None,
            processing_time=processing_time,
            chunks_per_second=0.0,
            chunking_statistics={'total_chunks': 0},
            warnings=[reason],
            recommendations=["Provide valid text content for chunking"]
        )
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get global processing statistics"""
        stats = self.processing_stats.copy()
        
        if stats['total_documents'] > 0:
            stats['avg_chunks_per_doc'] = stats['total_chunks_created'] / stats['total_documents']
            stats['avg_processing_time_per_doc'] = stats['total_processing_time'] / stats['total_documents']
        
        return stats
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.processing_stats = {
            'total_documents': 0,
            'content_aware_used': 0,
            'fallback_used': 0,
            'hybrid_used': 0,
            'total_chunks_created': 0,
            'total_processing_time': 0.0
        }