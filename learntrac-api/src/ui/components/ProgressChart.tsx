/**
 * Progress Chart Component
 * 
 * Visualizes learning progress over time
 */

import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { LearningProgress } from '../types/api';

interface ProgressChartProps {
  progress: LearningProgress[];
  timeRange: 'week' | 'month' | 'all';
  showMastery?: boolean;
}

const ProgressChart: React.FC<ProgressChartProps> = ({
  progress,
  timeRange,
  showMastery = true
}) => {
  // Process data for chart
  const chartData = progress.map(p => ({
    concept: p.concept_name.length > 20 
      ? p.concept_name.substring(0, 20) + '...' 
      : p.concept_name,
    understanding: Math.round(p.understanding_level * 100),
    mastery: Math.round(p.mastery_score * 100),
    time: p.time_spent_minutes
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="tooltip-entry" style={{ color: entry.color }}>
              {entry.name}: {entry.value}%
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="progress-chart">
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <defs>
            <linearGradient id="understandingGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
            </linearGradient>
            <linearGradient id="masteryGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis 
            dataKey="concept" 
            stroke="#6b7280"
            tick={{ fontSize: 12 }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis 
            stroke="#6b7280"
            tick={{ fontSize: 12 }}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="rect"
          />
          <Area
            type="monotone"
            dataKey="understanding"
            stroke="#3b82f6"
            fillOpacity={1}
            fill="url(#understandingGradient)"
            name="Understanding"
            strokeWidth={2}
          />
          {showMastery && (
            <Area
              type="monotone"
              dataKey="mastery"
              stroke="#10b981"
              fillOpacity={1}
              fill="url(#masteryGradient)"
              name="Mastery"
              strokeWidth={2}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ProgressChart;