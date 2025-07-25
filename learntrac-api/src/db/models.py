"""
Database models for LearnTrac learning schema
Uses SQLAlchemy with async support
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, Float, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class LearningPath(Base):
    """Learning paths that contain ordered concepts"""
    __tablename__ = 'learning_paths'
    __table_args__ = {'schema': 'learning'}
    
    path_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    difficulty_level = Column(String(20), nullable=False, default='intermediate')
    estimated_hours = Column(Integer)
    prerequisites_json = Column(JSON)
    tags = Column(JSON)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(50))
    
    # Relationships
    concepts = relationship("ConceptMetadata", back_populates="path")
    
    # Indexes
    __table_args__ = (
        Index('idx_paths_active', 'active'),
        Index('idx_paths_created_at', 'created_at'),
        {'schema': 'learning'}
    )


class ConceptMetadata(Base):
    """Metadata for learning concepts linked to Trac tickets"""
    __tablename__ = 'concept_metadata'
    __table_args__ = {'schema': 'learning'}
    
    concept_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(Integer, nullable=False)  # References public.ticket(id)
    path_id = Column(UUID(as_uuid=True), ForeignKey('learning.learning_paths.path_id', ondelete='CASCADE'))
    sequence_order = Column(Integer, nullable=False)
    concept_type = Column(String(50), nullable=False, default='lesson')
    difficulty_score = Column(Integer, default=5)
    mastery_threshold = Column(Float, default=0.8)
    practice_questions = Column(JSON)
    learning_objectives = Column(JSON)
    resources = Column(JSON)
    estimated_minutes = Column(Integer)
    tags = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    path = relationship("LearningPath", back_populates="concepts")
    prerequisites = relationship("Prerequisite", foreign_keys="Prerequisite.concept_id", back_populates="concept")
    progress_records = relationship("Progress", back_populates="concept")
    
    # Indexes
    __table_args__ = (
        Index('idx_concepts_ticket', 'ticket_id'),
        Index('idx_concepts_path_order', 'path_id', 'sequence_order'),
        {'schema': 'learning'}
    )


class Prerequisite(Base):
    """Prerequisites between concepts"""
    __tablename__ = 'prerequisites'
    __table_args__ = {'schema': 'learning'}
    
    prerequisite_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id = Column(UUID(as_uuid=True), ForeignKey('learning.concept_metadata.concept_id', ondelete='CASCADE'))
    prereq_concept_id = Column(UUID(as_uuid=True), ForeignKey('learning.concept_metadata.concept_id', ondelete='CASCADE'))
    requirement_type = Column(String(20), nullable=False, default='mandatory')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    concept = relationship("ConceptMetadata", foreign_keys=[concept_id], back_populates="prerequisites")
    prerequisite_concept = relationship("ConceptMetadata", foreign_keys=[prereq_concept_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_prereqs_concept', 'concept_id'),
        Index('idx_prereqs_prereq', 'prereq_concept_id'),
        {'schema': 'learning'}
    )


class Progress(Base):
    """Student progress tracking"""
    __tablename__ = 'progress'
    __table_args__ = {'schema': 'learning'}
    
    progress_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(100), nullable=False)  # From Cognito sub
    concept_id = Column(UUID(as_uuid=True), ForeignKey('learning.concept_metadata.concept_id', ondelete='CASCADE'))
    ticket_id = Column(Integer, nullable=False)  # Denormalized for performance
    status = Column(String(20), nullable=False, default='not_started')
    mastery_score = Column(Float, default=0.0)
    time_spent_minutes = Column(Integer, default=0)
    attempt_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    practice_results = Column(JSON)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    concept = relationship("ConceptMetadata", back_populates="progress_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_progress_student', 'student_id'),
        Index('idx_progress_student_concept', 'student_id', 'concept_id', unique=True),
        Index('idx_progress_status', 'status'),
        Index('idx_progress_ticket', 'ticket_id'),
        {'schema': 'learning'}
    )