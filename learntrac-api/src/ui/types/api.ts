/**
 * API Type Definitions for UI Components
 */

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: 'student' | 'instructor' | 'admin';
  level: 'beginner' | 'intermediate' | 'advanced';
  interests: string[];
  total_time_minutes: number;
  concepts_mastered: string[];
  created_at: string;
}

export interface SearchResult {
  chunk_id: string;
  score: number;
  text: string;
  textbook_title: string;
  chapter_title: string;
  section_title?: string;
  concepts: string[];
  difficulty: number;
  explanation: string;
}

export interface ContentFilter {
  subjects: string[];
  difficulty: {
    min: number;
    max: number;
  };
  textbooks: string[];
  concepts: string[];
}

export interface LearningProgress {
  concept_id: string;
  concept_name: string;
  understanding_level: number;
  time_spent_minutes: number;
  last_accessed: string;
  completed_chunks: string[];
  mastery_score: number;
}

export interface Recommendation {
  chunk_id: string;
  score: number;
  reason: string;
  concept: string;
  difficulty: number;
  estimated_time_minutes: number;
  prerequisites_met: boolean;
}

export interface LearningPath {
  path_id: string;
  segments: number;
  total_chunks: number;
  completed_chunks: number;
  estimated_time_hours: number;
  target_concepts: string[];
  next_segments?: {
    name: string;
    chunks: number;
    completed: boolean;
  }[];
}

export interface AnalyticsOverview {
  user_level: 'beginner' | 'intermediate' | 'advanced';
  total_time_hours: number;
  total_concepts_studied: number;
  concepts_mastered: number;
  average_understanding: number;
  learning_streak_days: number;
  recent_activity: Array<{
    chunk_id: string;
    timestamp: string;
    understanding_level: number;
    concepts: string[];
  }>;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface FilterOptions {
  subjects: string[];
  textbooks: { id: string; title: string }[];
  concepts: string[];
}