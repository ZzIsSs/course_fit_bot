import React from 'react';

interface ProgressBarProps {
  value: number; // 0 -> 100
  height?: number;
  showLabel?: boolean;
  className?: string;
  color?: 'brand' | 'emerald' | 'gradient';
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value = 0,
  height = 8,
  showLabel = false,
  className = '',
  color = 'emerald',
}) => {
  // Defensive: Clamp giữa 0 và 100, xử lý NaN
  const safeValue = isNaN(value) ? 0 : Math.min(100, Math.max(0, value));

  const colorStyles = {
    brand: 'bg-brand-600',
    emerald: 'bg-emerald-500',
    gradient: 'bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500',
  }[color];

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between items-center text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
          <span>Tiến độ hoàn thành</span>
          <span>{safeValue.toFixed(1)}%</span>
        </div>
      )}
      <div
        className="w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden"
        style={{ height: `${height}px` }}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${colorStyles}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
};
