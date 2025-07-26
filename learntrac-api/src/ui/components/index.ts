/**
 * UI Components Export
 * 
 * Central export point for all Trac UI components
 */

// Search Components
export { default as SearchInterface } from './SearchInterface';
export { default as ContentCard } from './ContentCard';
export { default as FilterPanel } from './FilterPanel';
export { default as RangeSlider } from './RangeSlider';

// Dashboard Components
export { default as LearningDashboard } from './LearningDashboard';
export { default as ProgressChart } from './ProgressChart';
export { default as RecommendationCard } from './RecommendationCard';
export { default as LearningPathCard } from './LearningPathCard';
export { default as ActivityFeed } from './ActivityFeed';

// Export types
export * from '../types/api';

// Export hooks
export { useTracAPI } from '../hooks/useTracAPI';