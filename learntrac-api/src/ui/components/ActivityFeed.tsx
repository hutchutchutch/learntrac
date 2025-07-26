/**
 * Activity Feed Component
 * 
 * Displays recent learning activities
 */

import React from 'react';
import {
  BookOpen,
  CheckCircle,
  Clock,
  TrendingUp,
  Award,
  FileText
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { motion } from 'framer-motion';

interface Activity {
  chunk_id: string;
  timestamp: string;
  understanding_level: number;
  concepts: string[];
  type?: 'study' | 'complete' | 'mastery' | 'review';
}

interface ActivityFeedProps {
  activities: Activity[];
  limit?: number;
  showAll?: boolean;
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({
  activities,
  limit = 10,
  showAll = false
}) => {
  const displayActivities = showAll ? activities : activities.slice(0, limit);

  const getActivityIcon = (activity: Activity) => {
    if (activity.understanding_level >= 0.8) {
      return <Award className="activity-icon mastery" size={16} />;
    } else if (activity.understanding_level >= 0.7) {
      return <CheckCircle className="activity-icon complete" size={16} />;
    } else if (activity.type === 'review') {
      return <FileText className="activity-icon review" size={16} />;
    } else {
      return <BookOpen className="activity-icon study" size={16} />;
    }
  };

  const getActivityMessage = (activity: Activity) => {
    const conceptText = activity.concepts.slice(0, 2).join(', ');
    
    if (activity.understanding_level >= 0.8) {
      return `Mastered ${conceptText}`;
    } else if (activity.understanding_level >= 0.7) {
      return `Completed ${conceptText}`;
    } else if (activity.type === 'review') {
      return `Reviewed ${conceptText}`;
    } else {
      return `Studied ${conceptText}`;
    }
  };

  const getUnderstandingColor = (level: number) => {
    if (level >= 0.8) return 'understanding-high';
    if (level >= 0.5) return 'understanding-medium';
    return 'understanding-low';
  };

  if (displayActivities.length === 0) {
    return (
      <div className="activity-feed empty">
        <Clock size={32} className="empty-icon" />
        <p>No recent activity</p>
      </div>
    );
  }

  return (
    <div className="activity-feed">
      {displayActivities.map((activity, index) => (
        <motion.div
          key={`${activity.chunk_id}-${activity.timestamp}`}
          className="activity-item"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <div className="activity-icon-wrapper">
            {getActivityIcon(activity)}
          </div>
          
          <div className="activity-content">
            <p className="activity-message">
              {getActivityMessage(activity)}
            </p>
            <div className="activity-meta">
              <span className="activity-time">
                {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
              </span>
              <span className={`activity-understanding ${getUnderstandingColor(activity.understanding_level)}`}>
                {Math.round(activity.understanding_level * 100)}% understanding
              </span>
            </div>
          </div>
          
          <div className="activity-progress">
            <div className="progress-circle">
              <svg width="32" height="32">
                <circle
                  cx="16"
                  cy="16"
                  r="14"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="2"
                />
                <circle
                  cx="16"
                  cy="16"
                  r="14"
                  fill="none"
                  stroke={activity.understanding_level >= 0.8 ? '#10b981' : '#3b82f6'}
                  strokeWidth="2"
                  strokeDasharray={`${2 * Math.PI * 14 * activity.understanding_level} ${2 * Math.PI * 14}`}
                  strokeDashoffset="0"
                  transform="rotate(-90 16 16)"
                />
              </svg>
            </div>
          </div>
        </motion.div>
      ))}
      
      {!showAll && activities.length > limit && (
        <div className="activity-more">
          <p>{activities.length - limit} more activities</p>
        </div>
      )}
    </div>
  );
};

export default ActivityFeed;