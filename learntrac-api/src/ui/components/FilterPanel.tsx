/**
 * Filter Panel Component
 * 
 * Advanced filtering options for educational content:
 * - Subject selection
 * - Difficulty range
 * - Textbook filtering
 * - Concept selection
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  ChevronDown,
  ChevronUp,
  Check,
  RotateCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ContentFilter } from '../types/api';
import { useTracAPI } from '../hooks/useTracAPI';
import RangeSlider from './RangeSlider';

interface FilterPanelProps {
  filters: ContentFilter;
  onFiltersChange: (filters: ContentFilter) => void;
  onClose?: () => void;
}

interface FilterSection {
  id: string;
  title: string;
  isExpanded: boolean;
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFiltersChange,
  onClose
}) => {
  const { getFilterOptions } = useTracAPI();
  const [filterOptions, setFilterOptions] = useState({
    subjects: [] as string[],
    textbooks: [] as { id: string; title: string }[],
    concepts: [] as string[]
  });
  
  const [sections, setSections] = useState<FilterSection[]>([
    { id: 'subjects', title: 'Subjects', isExpanded: true },
    { id: 'difficulty', title: 'Difficulty Level', isExpanded: true },
    { id: 'textbooks', title: 'Textbooks', isExpanded: false },
    { id: 'concepts', title: 'Concepts', isExpanded: false }
  ]);

  useEffect(() => {
    // Load filter options
    const loadOptions = async () => {
      try {
        const options = await getFilterOptions();
        setFilterOptions(options);
      } catch (error) {
        console.error('Failed to load filter options:', error);
      }
    };
    loadOptions();
  }, [getFilterOptions]);

  const toggleSection = (sectionId: string) => {
    setSections(prev => 
      prev.map(section => 
        section.id === sectionId 
          ? { ...section, isExpanded: !section.isExpanded }
          : section
      )
    );
  };

  const handleSubjectToggle = (subject: string) => {
    const newSubjects = filters.subjects.includes(subject)
      ? filters.subjects.filter(s => s !== subject)
      : [...filters.subjects, subject];
    
    onFiltersChange({ ...filters, subjects: newSubjects });
  };

  const handleTextbookToggle = (textbookId: string) => {
    const newTextbooks = filters.textbooks.includes(textbookId)
      ? filters.textbooks.filter(t => t !== textbookId)
      : [...filters.textbooks, textbookId];
    
    onFiltersChange({ ...filters, textbooks: newTextbooks });
  };

  const handleConceptToggle = (concept: string) => {
    const newConcepts = filters.concepts.includes(concept)
      ? filters.concepts.filter(c => c !== concept)
      : [...filters.concepts, concept];
    
    onFiltersChange({ ...filters, concepts: newConcepts });
  };

  const handleDifficultyChange = (values: [number, number]) => {
    onFiltersChange({
      ...filters,
      difficulty: { min: values[0], max: values[1] }
    });
  };

  const resetFilters = () => {
    onFiltersChange({
      subjects: [],
      difficulty: { min: 0, max: 1 },
      textbooks: [],
      concepts: []
    });
  };

  const hasActiveFilters = 
    filters.subjects.length > 0 ||
    filters.textbooks.length > 0 ||
    filters.concepts.length > 0 ||
    filters.difficulty.min > 0 ||
    filters.difficulty.max < 1;

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h3>Filters</h3>
        <div className="filter-actions">
          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="reset-button"
              aria-label="Reset filters"
            >
              <RotateCcw size={16} />
              <span>Reset</span>
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="close-button"
              aria-label="Close filters"
            >
              <X size={20} />
            </button>
          )}
        </div>
      </div>

      <div className="filter-sections">
        {/* Subjects Section */}
        <div className="filter-section">
          <button
            className="section-header"
            onClick={() => toggleSection('subjects')}
          >
            <span className="section-title">Subjects</span>
            <span className="section-count">
              {filters.subjects.length > 0 && `(${filters.subjects.length})`}
            </span>
            {sections.find(s => s.id === 'subjects')?.isExpanded
              ? <ChevronUp size={16} />
              : <ChevronDown size={16} />
            }
          </button>
          
          <AnimatePresence>
            {sections.find(s => s.id === 'subjects')?.isExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="section-content"
              >
                <div className="checkbox-list">
                  {filterOptions.subjects.map(subject => (
                    <label key={subject} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={filters.subjects.includes(subject)}
                        onChange={() => handleSubjectToggle(subject)}
                      />
                      <span className="checkbox-custom">
                        {filters.subjects.includes(subject) && <Check size={12} />}
                      </span>
                      <span className="checkbox-label">{subject}</span>
                    </label>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Difficulty Section */}
        <div className="filter-section">
          <button
            className="section-header"
            onClick={() => toggleSection('difficulty')}
          >
            <span className="section-title">Difficulty Level</span>
            {sections.find(s => s.id === 'difficulty')?.isExpanded
              ? <ChevronUp size={16} />
              : <ChevronDown size={16} />
            }
          </button>
          
          <AnimatePresence>
            {sections.find(s => s.id === 'difficulty')?.isExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="section-content"
              >
                <div className="difficulty-slider">
                  <RangeSlider
                    min={0}
                    max={1}
                    step={0.1}
                    values={[filters.difficulty.min, filters.difficulty.max]}
                    onChange={handleDifficultyChange}
                    labels={['Beginner', 'Intermediate', 'Advanced']}
                  />
                  <div className="difficulty-labels">
                    <span>Beginner</span>
                    <span>Advanced</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Textbooks Section */}
        <div className="filter-section">
          <button
            className="section-header"
            onClick={() => toggleSection('textbooks')}
          >
            <span className="section-title">Textbooks</span>
            <span className="section-count">
              {filters.textbooks.length > 0 && `(${filters.textbooks.length})`}
            </span>
            {sections.find(s => s.id === 'textbooks')?.isExpanded
              ? <ChevronUp size={16} />
              : <ChevronDown size={16} />
            }
          </button>
          
          <AnimatePresence>
            {sections.find(s => s.id === 'textbooks')?.isExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="section-content"
              >
                <div className="checkbox-list">
                  {filterOptions.textbooks.map(textbook => (
                    <label key={textbook.id} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={filters.textbooks.includes(textbook.id)}
                        onChange={() => handleTextbookToggle(textbook.id)}
                      />
                      <span className="checkbox-custom">
                        {filters.textbooks.includes(textbook.id) && <Check size={12} />}
                      </span>
                      <span className="checkbox-label">{textbook.title}</span>
                    </label>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Concepts Section */}
        <div className="filter-section">
          <button
            className="section-header"
            onClick={() => toggleSection('concepts')}
          >
            <span className="section-title">Concepts</span>
            <span className="section-count">
              {filters.concepts.length > 0 && `(${filters.concepts.length})`}
            </span>
            {sections.find(s => s.id === 'concepts')?.isExpanded
              ? <ChevronUp size={16} />
              : <ChevronDown size={16} />
            }
          </button>
          
          <AnimatePresence>
            {sections.find(s => s.id === 'concepts')?.isExpanded && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="section-content"
              >
                <div className="checkbox-list scrollable">
                  {filterOptions.concepts.map(concept => (
                    <label key={concept} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={filters.concepts.includes(concept)}
                        onChange={() => handleConceptToggle(concept)}
                      />
                      <span className="checkbox-custom">
                        {filters.concepts.includes(concept) && <Check size={12} />}
                      </span>
                      <span className="checkbox-label">{concept}</span>
                    </label>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default FilterPanel;