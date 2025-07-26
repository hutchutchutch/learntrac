/**
 * Recommendation Card Component
 * 
 * Displays personalized content recommendations
 */

import React from 'react';
import {
  Star,
  Clock,
  CheckCircle,
  XCircle,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Recommendation } from '../types/api';

interface RecommendationCardProps {
  recommendation: Recommendation;
  onClick?: () => void;
  index: number;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onClick,
  index
}) => {
  const getDifficultyColor = (difficulty: number): string => {
    if (difficulty < 0.3) return 'difficulty-easy';
    if (difficulty < 0.7) return 'difficulty-medium';
    return 'difficulty-hard';
  };

  const getScoreColor = (score: number): string => {
    if (score > 0.8) return 'score-high';
    if (score > 0.5) return 'score-medium';
    return 'score-low';
  };

  return (
    <motion.div
      className="recommendation-card"
      onClick={onClick}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      whileHover={{ x: 5 }}
    >
      <div className="rec-header">
        <div className="rec-score">
          <Star className={`score-icon ${getScoreColor(recommendation.score)}`} size={16} />
          <span>{Math.round(recommendation.score * 100)}% match</span>
        </div>
        {recommendation.prerequisites_met ? (
          <CheckCircle className="prereq-icon met" size={16} />
        ) : (
          <AlertCircle className="prereq-icon not-met" size={16} />
        )}
      </div>

      <h4 className="rec-concept">{recommendation.concept}</h4>
      <p className="rec-reason">{recommendation.reason}</p>

      <div className="rec-footer">
        <div className="rec-meta">
          <span className={`difficulty-badge ${getDifficultyColor(recommendation.difficulty)}`}>
            {recommendation.difficulty < 0.3 ? 'Easy' : 
             recommendation.difficulty < 0.7 ? 'Medium' : 'Hard'}
          </span>
          <span className="time-estimate">
            <Clock size={14} />
            {recommendation.estimated_time_minutes} min
          </span>
        </div>
        <TrendingUp className="trending-icon" size={16} />
      </div>
    </motion.div>
  );
};

export default RecommendationCard;