/**
 * Learning Path Card Component
 * 
 * Shows current learning path progress and next steps
 */

import React from 'react';
import {
  Route,
  Target,
  Clock,
  CheckCircle2,
  Circle,
  ArrowRight
} from 'lucide-react';
import { motion } from 'framer-motion';
import { LearningPath } from '../types/api';

interface LearningPathCardProps {
  path: LearningPath;
  onContinue?: () => void;
}

const LearningPathCard: React.FC<LearningPathCardProps> = ({
  path,
  onContinue
}) => {
  const progressPercentage = (path.completed_chunks / path.total_chunks) * 100;

  return (
    <div className="learning-path-card">
      <div className="path-header">
        <div className="path-icon">
          <Route size={24} />
        </div>
        <div className="path-info">
          <h3>Learning Path #{path.path_id.slice(0, 8)}</h3>
          <p className="path-targets">
            {path.target_concepts.join(', ')}
          </p>
        </div>
      </div>

      <div className="path-progress">
        <div className="progress-stats">
          <div className="stat">
            <Target size={16} />
            <span>{path.segments} segments</span>
          </div>
          <div className="stat">
            <Clock size={16} />
            <span>{path.estimated_time_hours}h estimated</span>
          </div>
        </div>

        <div className="progress-bar-container">
          <div className="progress-bar-background">
            <motion.div
              className="progress-bar-fill"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercentage}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
          <span className="progress-text">
            {path.completed_chunks} / {path.total_chunks} completed
          </span>
        </div>
      </div>

      <div className="path-segments">
        <h4>Next Up</h4>
        <div className="segment-list">
          {path.next_segments?.slice(0, 3).map((segment, index) => (
            <div key={index} className="segment-item">
              {segment.completed ? (
                <CheckCircle2 className="segment-icon completed" size={16} />
              ) : (
                <Circle className="segment-icon pending" size={16} />
              )}
              <span className="segment-name">{segment.name}</span>
              <span className="segment-chunks">({segment.chunks} items)</span>
            </div>
          ))}
        </div>
      </div>

      {onContinue && (
        <button 
          className="continue-button"
          onClick={onContinue}
        >
          Continue Learning
          <ArrowRight size={16} />
        </button>
      )}
    </div>
  );
};

export default LearningPathCard;