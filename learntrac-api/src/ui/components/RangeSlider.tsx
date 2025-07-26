/**
 * Range Slider Component
 * 
 * Dual-handle range slider for selecting value ranges
 */

import React, { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';

interface RangeSliderProps {
  min: number;
  max: number;
  step: number;
  values: [number, number];
  onChange: (values: [number, number]) => void;
  labels?: string[];
  formatValue?: (value: number) => string;
}

const RangeSlider: React.FC<RangeSliderProps> = ({
  min,
  max,
  step,
  values,
  onChange,
  labels,
  formatValue = (v) => v.toFixed(1)
}) => {
  const [isDragging, setIsDragging] = useState<'min' | 'max' | null>(null);
  const sliderRef = useRef<HTMLDivElement>(null);
  const [localValues, setLocalValues] = useState(values);

  useEffect(() => {
    setLocalValues(values);
  }, [values]);

  const getPercentage = (value: number) => {
    return ((value - min) / (max - min)) * 100;
  };

  const getValue = (percentage: number) => {
    const value = (percentage / 100) * (max - min) + min;
    return Math.round(value / step) * step;
  };

  const handleMouseDown = (handle: 'min' | 'max') => {
    setIsDragging(handle);
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !sliderRef.current) return;

    const rect = sliderRef.current.getBoundingClientRect();
    const percentage = Math.max(0, Math.min(100, 
      ((e.clientX - rect.left) / rect.width) * 100
    ));
    const value = getValue(percentage);

    const newValues: [number, number] = [...localValues];
    
    if (isDragging === 'min') {
      newValues[0] = Math.min(value, localValues[1] - step);
    } else {
      newValues[1] = Math.max(value, localValues[0] + step);
    }

    setLocalValues(newValues);
    onChange(newValues);
  };

  const handleMouseUp = () => {
    setIsDragging(null);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, localValues]);

  const minPercentage = getPercentage(localValues[0]);
  const maxPercentage = getPercentage(localValues[1]);

  return (
    <div className="range-slider">
      <div className="slider-container" ref={sliderRef}>
        {/* Track */}
        <div className="slider-track">
          <motion.div
            className="slider-range"
            style={{
              left: `${minPercentage}%`,
              width: `${maxPercentage - minPercentage}%`
            }}
            layout
          />
        </div>

        {/* Min Handle */}
        <motion.div
          className={`slider-handle ${isDragging === 'min' ? 'dragging' : ''}`}
          style={{ left: `${minPercentage}%` }}
          onMouseDown={() => handleMouseDown('min')}
          whileHover={{ scale: 1.2 }}
          whileTap={{ scale: 0.9 }}
        >
          <div className="handle-tooltip">
            {formatValue(localValues[0])}
          </div>
        </motion.div>

        {/* Max Handle */}
        <motion.div
          className={`slider-handle ${isDragging === 'max' ? 'dragging' : ''}`}
          style={{ left: `${maxPercentage}%` }}
          onMouseDown={() => handleMouseDown('max')}
          whileHover={{ scale: 1.2 }}
          whileTap={{ scale: 0.9 }}
        >
          <div className="handle-tooltip">
            {formatValue(localValues[1])}
          </div>
        </motion.div>
      </div>

      {/* Labels */}
      {labels && labels.length > 0 && (
        <div className="slider-labels">
          {labels.map((label, index) => (
            <span
              key={index}
              className="slider-label"
              style={{
                left: `${(index / (labels.length - 1)) * 100}%`
              }}
            >
              {label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default RangeSlider;