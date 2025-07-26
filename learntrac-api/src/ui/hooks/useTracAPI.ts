/**
 * Trac API Hook
 * 
 * Custom React hook for interacting with Trac API endpoints
 */

import { useState, useCallback } from 'react';
import axios, { AxiosInstance } from 'axios';
import {
  User,
  SearchResult,
  ContentFilter,
  LearningProgress,
  Recommendation,
  LearningPath,
  AnalyticsOverview,
  AuthToken,
  FilterOptions
} from '../types/api';

interface UseTracAPIOptions {
  baseURL?: string;
  onAuthError?: () => void;
}

export const useTracAPI = (options: UseTracAPIOptions = {}) => {
  const {
    baseURL = process.env.REACT_APP_API_URL || '/api/trac',
    onAuthError
  } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Create axios instance
  const api: AxiosInstance = axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Add auth token to requests
  api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Handle auth errors
  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      if (error.response?.status === 401) {
        // Try to refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            const response = await axios.post(`${baseURL}/auth/refresh`, {
              refresh_token: refreshToken
            });
            
            const { access_token, refresh_token: newRefreshToken } = response.data;
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('refresh_token', newRefreshToken);
            
            // Retry original request
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return api.request(error.config);
          } catch (refreshError) {
            // Refresh failed
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            onAuthError?.();
          }
        } else {
          onAuthError?.();
        }
      }
      return Promise.reject(error);
    }
  );

  // Auth methods
  const login = useCallback(async (emailOrUsername: string, password: string): Promise<AuthToken> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('/auth/login', {
        email_or_username: emailOrUsername,
        password
      });
      
      const tokens = response.data;
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      
      return tokens;
    } catch (err: any) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [api]);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }, [api]);

  const register = useCallback(async (userData: {
    email: string;
    username: string;
    password: string;
    full_name: string;
    role?: string;
  }): Promise<User> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('/auth/register', userData);
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [api]);

  // Search methods
  const searchContent = useCallback(async (params: {
    query: string;
    filters?: ContentFilter;
    limit?: number;
  }): Promise<SearchResult[]> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post('/search', params);
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [api]);

  const getSearchSuggestions = useCallback(async (query: string): Promise<string[]> => {
    try {
      const response = await api.get('/search/suggestions', {
        params: { q: query }
      });
      return response.data.suggestions || [];
    } catch (err) {
      console.error('Failed to get suggestions:', err);
      return [];
    }
  }, [api]);

  const getFilterOptions = useCallback(async (): Promise<FilterOptions> => {
    try {
      const response = await api.get('/search/filters');
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  // Learning progress methods
  const trackProgress = useCallback(async (data: {
    chunk_id: string;
    time_spent_seconds: number;
    understanding_level: number;
  }): Promise<void> => {
    try {
      await api.post('/progress/track', data);
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  const getLearningProgress = useCallback(async (
    userId: string,
    conceptId?: string
  ): Promise<LearningProgress[]> => {
    try {
      const response = await api.get('/progress', {
        params: { concept_id: conceptId }
      });
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  // Recommendations
  const getRecommendations = useCallback(async (
    userId: string,
    limit: number = 10
  ): Promise<Recommendation[]> => {
    try {
      const response = await api.get('/recommendations', {
        params: { limit }
      });
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  // Learning paths
  const createLearningPath = useCallback(async (data: {
    target_concepts: string[];
    time_limit_hours?: number;
  }): Promise<LearningPath> => {
    try {
      const response = await api.post('/learning-paths', data);
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  const getCurrentLearningPath = useCallback(async (
    userId: string
  ): Promise<LearningPath | null> => {
    try {
      const response = await api.get('/learning-paths/current');
      return response.data;
    } catch (err: any) {
      if (err.response?.status === 404) {
        return null;
      }
      setError(err);
      throw err;
    }
  }, [api]);

  // Analytics
  const getAnalyticsOverview = useCallback(async (
    userId: string,
    timeRange: 'week' | 'month' | 'all' = 'week'
  ): Promise<AnalyticsOverview> => {
    try {
      const response = await api.get('/analytics/overview', {
        params: { time_range: timeRange }
      });
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  // Profile
  const getProfile = useCallback(async (): Promise<User> => {
    try {
      const response = await api.get('/profile');
      return response.data;
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  const updateProfile = useCallback(async (updates: Partial<User>): Promise<void> => {
    try {
      await api.put('/profile', updates);
    } catch (err: any) {
      setError(err);
      throw err;
    }
  }, [api]);

  return {
    // State
    isLoading,
    error,
    
    // Auth
    login,
    logout,
    register,
    
    // Search
    searchContent,
    getSearchSuggestions,
    getFilterOptions,
    
    // Progress
    trackProgress,
    getLearningProgress,
    
    // Recommendations
    getRecommendations,
    
    // Learning paths
    createLearningPath,
    getCurrentLearningPath,
    
    // Analytics
    getAnalyticsOverview,
    
    // Profile
    getProfile,
    updateProfile
  };
};