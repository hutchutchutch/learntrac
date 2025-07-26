/**
 * Educational Content Search Interface Component
 * 
 * Provides an intuitive search interface for educational content with:
 * - Smart query suggestions
 * - Filter options
 * - Real-time search results
 * - Content preview
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import debounce from 'lodash/debounce';
import {
  Search,
  Filter,
  BookOpen,
  Clock,
  TrendingUp,
  ChevronRight,
  X,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTracAPI } from '../hooks/useTracAPI';
import { SearchResult, ContentFilter } from '../types/api';
import ContentCard from './ContentCard';
import FilterPanel from './FilterPanel';

interface SearchInterfaceProps {
  onSelectContent?: (content: SearchResult) => void;
  initialQuery?: string;
  showFilters?: boolean;
}

const SearchInterface: React.FC<SearchInterfaceProps> = ({
  onSelectContent,
  initialQuery = '',
  showFilters = true
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [filters, setFilters] = useState<ContentFilter>({
    subjects: [],
    difficulty: { min: 0, max: 1 },
    textbooks: [],
    concepts: []
  });
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const searchInputRef = useRef<HTMLInputElement>(null);
  const { searchContent, getSearchSuggestions } = useTracAPI();

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string, searchFilters: ContentFilter) => {
      if (!searchQuery.trim()) {
        setResults([]);
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const searchResults = await searchContent({
          query: searchQuery,
          filters: searchFilters,
          limit: 20
        });
        setResults(searchResults);
      } catch (err) {
        setError('Failed to search content. Please try again.');
        console.error('Search error:', err);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    [searchContent]
  );

  // Debounced suggestions function
  const debouncedSuggestions = useCallback(
    debounce(async (searchQuery: string) => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        return;
      }

      try {
        const searchSuggestions = await getSearchSuggestions(searchQuery);
        setSuggestions(searchSuggestions);
      } catch (err) {
        console.error('Suggestions error:', err);
      }
    }, 150),
    [getSearchSuggestions]
  );

  // Effect for search
  useEffect(() => {
    debouncedSearch(query, filters);
  }, [query, filters, debouncedSearch]);

  // Effect for suggestions
  useEffect(() => {
    debouncedSuggestions(query);
  }, [query, debouncedSuggestions]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          setQuery(suggestions[selectedIndex]);
          setSuggestions([]);
          setSelectedIndex(-1);
        }
        break;
      case 'Escape':
        setSuggestions([]);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setSuggestions([]);
    setSelectedIndex(-1);
    searchInputRef.current?.focus();
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setSuggestions([]);
    setError(null);
    searchInputRef.current?.focus();
  };

  const activeFilterCount = [
    filters.subjects.length,
    filters.textbooks.length,
    filters.concepts.length,
    filters.difficulty.min > 0 || filters.difficulty.max < 1 ? 1 : 0
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="search-interface">
      {/* Search Header */}
      <div className="search-header">
        <div className="search-input-container">
          <div className="search-input-wrapper">
            <Search className="search-icon" size={20} />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search for concepts, topics, or questions..."
              className="search-input"
              autoComplete="off"
            />
            {query && (
              <button
                onClick={clearSearch}
                className="clear-button"
                aria-label="Clear search"
              >
                <X size={16} />
              </button>
            )}
            {isLoading && (
              <Loader2 className="loading-icon" size={16} />
            )}
          </div>

          {/* Search Suggestions */}
          <AnimatePresence>
            {suggestions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="suggestions-dropdown"
              >
                {suggestions.map((suggestion, index) => (
                  <div
                    key={suggestion}
                    className={`suggestion-item ${
                      index === selectedIndex ? 'selected' : ''
                    }`}
                    onClick={() => handleSuggestionClick(suggestion)}
                    onMouseEnter={() => setSelectedIndex(index)}
                  >
                    <Search size={14} className="suggestion-icon" />
                    <span>{suggestion}</span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Filter Toggle */}
        {showFilters && (
          <button
            onClick={() => setShowFilterPanel(!showFilterPanel)}
            className={`filter-toggle ${showFilterPanel ? 'active' : ''}`}
          >
            <Filter size={18} />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="filter-count">{activeFilterCount}</span>
            )}
          </button>
        )}
      </div>

      {/* Filter Panel */}
      <AnimatePresence>
        {showFilterPanel && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <FilterPanel
              filters={filters}
              onFiltersChange={setFilters}
              onClose={() => setShowFilterPanel(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Search Results */}
      <div className="search-results">
        {results.length > 0 ? (
          <>
            <div className="results-header">
              <h3>Search Results</h3>
              <span className="results-count">
                {results.length} {results.length === 1 ? 'result' : 'results'}
              </span>
            </div>
            <div className="results-grid">
              {results.map((result) => (
                <ContentCard
                  key={result.chunk_id}
                  content={result}
                  onClick={() => onSelectContent?.(result)}
                />
              ))}
            </div>
          </>
        ) : query && !isLoading && (
          <div className="no-results">
            <BookOpen size={48} className="no-results-icon" />
            <h3>No results found</h3>
            <p>Try adjusting your search terms or filters</p>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      {!query && !isLoading && (
        <div className="quick-stats">
          <h3>Popular Topics</h3>
          <div className="topic-grid">
            {['Machine Learning', 'Data Structures', 'Algorithms', 'Databases'].map(
              (topic) => (
                <button
                  key={topic}
                  className="topic-chip"
                  onClick={() => setQuery(topic)}
                >
                  <TrendingUp size={14} />
                  <span>{topic}</span>
                </button>
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchInterface;