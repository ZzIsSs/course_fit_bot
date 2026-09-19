import React from 'react';
import { Check } from 'lucide-react';

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  className?: string;
}

export const Checkbox: React.FC<CheckboxProps> = ({
  checked,
  onChange,
  disabled = false,
  label,
  className = '',
}) => {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled) {
      onChange(!checked);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      if (!disabled) {
        onChange(!checked);
      }
    }
  };

  return (
    <div
      role="checkbox"
      aria-checked={checked}
      tabIndex={disabled ? -1 : 0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`inline-flex items-center gap-2 select-none cursor-pointer ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
    >
      <div
        className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all duration-150 ${
          checked
            ? 'bg-emerald-600 border-emerald-600 text-white shadow-sm'
            : 'border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 hover:border-slate-400'
        }`}
      >
        {checked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
      </div>
      {label && <span className="text-sm text-slate-700 dark:text-slate-200">{label}</span>}
    </div>
  );
};
