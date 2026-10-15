import React from 'react';
import { Flame, Clock, CheckCircle2, AlertTriangle, BookOpen, User } from 'lucide-react';

interface BadgeProps {
  variant?: 'urgent' | 'soon' | 'normal' | 'completed' | 'overdue' | 'moodle' | 'manual' | 'course' | 'default';
  children: React.ReactNode;
  icon?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  children,
  icon = true,
  className = '',
}) => {
  const styles = {
    urgent: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/50',
    soon: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/50',
    normal: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/50',
    completed: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700',
    overdue: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900/50',
    moodle: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900/50',
    manual: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-400 dark:border-purple-900/50',
    course: 'bg-slate-100 text-slate-800 font-semibold border-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700',
    default: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
  }[variant];

  const renderIcon = () => {
    if (!icon) return null;
    switch (variant) {
      case 'urgent':
        return <Flame className="w-3 h-3 shrink-0 text-red-500 animate-pulse" />;
      case 'soon':
        return <Clock className="w-3 h-3 shrink-0 text-amber-500" />;
      case 'normal':
        return <Clock className="w-3 h-3 shrink-0 text-emerald-500" />;
      case 'completed':
        return <CheckCircle2 className="w-3 h-3 shrink-0 text-slate-500" />;
      case 'overdue':
        return <AlertTriangle className="w-3 h-3 shrink-0 text-rose-500" />;
      case 'moodle':
        return <BookOpen className="w-3 h-3 shrink-0 text-blue-500" />;
      case 'manual':
        return <User className="w-3 h-3 shrink-0 text-purple-500" />;
      default:
        return null;
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border max-w-full truncate ${styles} ${className}`}
    >
      {renderIcon()}
      <span className="truncate">{children ?? ''}</span>
    </span>
  );
};
