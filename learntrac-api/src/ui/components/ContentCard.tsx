/**
 * Content Card Component
 * 
 * Displays educational content in a card format with:
 * - Title and preview text
 * - Difficulty indicator
 * - Concepts tags
 * - Source information
 */

import React from 'react';
import {
  BookOpen,
  Clock,
  Star,
  ChevronRight,
  Zap,
  Target
} from 'lucide-react';
import { motion } from 'framer-motion';
import { SearchResult } from '../types/api';

interface ContentCardProps {
  content: SearchResult;
  onClick?: () => void;
  showFullText?: boolean;
  isActive?: boolean;
}

const ContentCard: React.FC<ContentCardProps> = ({
  content,
  onClick,
  showFullText = false,
  isActive = false
}) => {
  const getDifficultyColor = (difficulty: number): string => {
    if (difficulty < 0.3) return 'difficulty-easy';
    if (difficulty < 0.7) return 'difficulty-medium';
    return 'difficulty-hard';
  };

  const getDifficultyLabel = (difficulty: number): string => {
    if (difficulty < 0.3) return 'Beginner';
    if (difficulty < 0.7) return 'Intermediate';
    return 'Advanced';
  };

  const getScoreIcon = (score: number) => {
    if (score > 0.8) return <Zap className="score-icon high" size={14} />;
    if (score > 0.5) return <Star className="score-icon medium" size={14} />;
    return <Target className="score-icon low" size={14} />;
  };

  const truncateText = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
  };

  return (
    <motion.div
      className={`content-card ${isActive ? 'active' : ''}`}
      onClick={onClick}
      whileHover={{ scale: 1.02, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Card Header */}
      <div className="card-header">
        <div className="source-info">
          <BookOpen size={14} />
          <span className="textbook-title">{content.textbook_title}</span>
          {content.chapter_title && (
            <>
              <ChevronRight size={12} className="separator" />
              <span className="chapter-title">{content.chapter_title}</span>
            </>
          )}
        </div>
        <div className="score-badge">
          {getScoreIcon(content.score)}
          <span>{Math.round(content.score * 100)}%</span>
        </div>
      </div>

      {/* Card Body */}
      <div className="card-body">
        <h4 className="content-title">
          {content.section_title || 'Content Section'}
        </h4>
        <p className="content-text">
          {showFullText
            ? content.text
            : truncateText(content.text, 200)
          }
        </p>

        {/* Explanation if available */}
        {content.explanation && (
          <div className="content-explanation">
            <span className="explanation-label">Why this matches:</span>
            <p>{content.explanation}</p>
          </div>
        )}
      </div>

      {/* Card Footer */}
      <div className="card-footer">
        <div className="concepts-container">
          {content.concepts.slice(0, 3).map((concept, index) => (
            <span key={index} className="concept-tag">
              {concept}
            </span>
          ))}
          {content.concepts.length > 3 && (
            <span className="concept-more">+{content.concepts.length - 3}</span>
          )}
        </div>
        
        <div className="card-meta">
          <span className={`difficulty-badge ${getDifficultyColor(content.difficulty)}`}>
            {getDifficultyLabel(content.difficulty)}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default ContentCard;