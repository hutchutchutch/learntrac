/**
 * Learning Dashboard Component
 * 
 * Main dashboard for tracking learning progress:
 * - Progress overview
 * - Recent activity
 * - Recommendations
 * - Learning paths
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Clock,
  Target,
  Award,
  BookOpen,
  Activity,
  Calendar,
  ChevronRight,
  BarChart3,
  Zap
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useTracAPI } from '../hooks/useTracAPI';
import { 
  LearningProgress, 
  AnalyticsOverview,
  Recommendation,
  LearningPath 
} from '../types/api';
import ProgressChart from './ProgressChart';
import RecommendationCard from './RecommendationCard';
import LearningPathCard from './LearningPathCard';
import ActivityFeed from './ActivityFeed';

interface LearningDashboardProps {
  userId: string;
}

const LearningDashboard: React.FC<LearningDashboardProps> = ({ userId }) => {
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [progress, setProgress] = useState<LearningProgress[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [currentPath, setCurrentPath] = useState<LearningPath | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState<'week' | 'month' | 'all'>('week');

  const { 
    getAnalyticsOverview, 
    getLearningProgress, 
    getRecommendations,
    getCurrentLearningPath 
  } = useTracAPI();

  useEffect(() => {
    loadDashboardData();
  }, [userId, selectedTimeRange]);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [analyticsData, progressData, recommendationsData, pathData] = await Promise.all([
        getAnalyticsOverview(userId, selectedTimeRange),
        getLearningProgress(userId),
        getRecommendations(userId, 5),
        getCurrentLearningPath(userId)
      ]);

      setAnalytics(analyticsData);
      setProgress(progressData);
      setRecommendations(recommendationsData);
      setCurrentPath(pathData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'beginner': return 'level-beginner';
      case 'intermediate': return 'level-intermediate';
      case 'advanced': return 'level-advanced';
      default: return 'level-beginner';
    }
  };

  const formatTime = (minutes: number): string => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  if (isLoading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner" />
        <p>Loading your learning dashboard...</p>
      </div>
    );
  }

  return (
    <div className="learning-dashboard">
      {/* Header Section */}
      <div className="dashboard-header">
        <h1>Learning Dashboard</h1>
        <div className="time-range-selector">
          {(['week', 'month', 'all'] as const).map(range => (
            <button
              key={range}
              className={`range-button ${selectedTimeRange === range ? 'active' : ''}`}
              onClick={() => setSelectedTimeRange(range)}
            >
              {range === 'week' ? 'This Week' : range === 'month' ? 'This Month' : 'All Time'}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Overview */}
      {analytics && (
        <div className="stats-grid">
          <motion.div 
            className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="stat-icon">
              <Clock size={24} />
            </div>
            <div className="stat-content">
              <h3>Study Time</h3>
              <p className="stat-value">{formatTime(analytics.total_time_hours * 60)}</p>
              <span className="stat-change positive">+12% this week</span>
            </div>
          </motion.div>

          <motion.div 
            className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="stat-icon">
              <Target size={24} />
            </div>
            <div className="stat-content">
              <h3>Concepts Studied</h3>
              <p className="stat-value">{analytics.total_concepts_studied}</p>
              <span className="stat-subtitle">across {progress.length} topics</span>
            </div>
          </motion.div>

          <motion.div 
            className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="stat-icon">
              <Award size={24} />
            </div>
            <div className="stat-content">
              <h3>Mastered</h3>
              <p className="stat-value">{analytics.concepts_mastered}</p>
              <div className="stat-progress">
                <div 
                  className="progress-bar"
                  style={{ 
                    width: `${(analytics.concepts_mastered / analytics.total_concepts_studied) * 100}%` 
                  }}
                />
              </div>
            </div>
          </motion.div>

          <motion.div 
            className="stat-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="stat-icon">
              <Zap size={24} />
            </div>
            <div className="stat-content">
              <h3>Learning Streak</h3>
              <p className="stat-value">{analytics.learning_streak_days} days</p>
              <span className="stat-subtitle">Keep it up!</span>
            </div>
          </motion.div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="dashboard-content">
        {/* Left Column */}
        <div className="dashboard-column left">
          {/* Progress Chart */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2>
                <BarChart3 size={20} />
                Learning Progress
              </h2>
              <span className={`level-badge ${getLevelColor(analytics?.user_level || 'beginner')}`}>
                {analytics?.user_level || 'Beginner'} Level
              </span>
            </div>
            <div className="card-body">
              <ProgressChart 
                progress={progress}
                timeRange={selectedTimeRange}
              />
            </div>
          </div>

          {/* Recent Activity */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2>
                <Activity size={20} />
                Recent Activity
              </h2>
              <button className="see-all-button">
                See all
                <ChevronRight size={16} />
              </button>
            </div>
            <div className="card-body">
              <ActivityFeed 
                activities={analytics?.recent_activity || []}
                limit={5}
              />
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="dashboard-column right">
          {/* Current Learning Path */}
          {currentPath && (
            <div className="dashboard-card">
              <div className="card-header">
                <h2>
                  <Target size={20} />
                  Current Learning Path
                </h2>
              </div>
              <div className="card-body">
                <LearningPathCard 
                  path={currentPath}
                  onContinue={() => console.log('Continue learning path')}
                />
              </div>
            </div>
          )}

          {/* Recommendations */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2>
                <TrendingUp size={20} />
                Recommended for You
              </h2>
              <button className="see-all-button">
                See all
                <ChevronRight size={16} />
              </button>
            </div>
            <div className="card-body">
              <div className="recommendations-list">
                {recommendations.map((rec, index) => (
                  <RecommendationCard
                    key={rec.chunk_id}
                    recommendation={rec}
                    index={index}
                    onClick={() => console.log('Open recommendation', rec.chunk_id)}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Study Schedule */}
          <div className="dashboard-card">
            <div className="card-header">
              <h2>
                <Calendar size={20} />
                Study Schedule
              </h2>
            </div>
            <div className="card-body">
              <div className="schedule-summary">
                <p>You've studied <strong>4 out of 7 days</strong> this week</p>
                <div className="schedule-grid">
                  {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, index) => (
                    <div 
                      key={index}
                      className={`schedule-day ${index < 4 ? 'completed' : ''} ${index === 4 ? 'today' : ''}`}
                    >
                      {day}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningDashboard;