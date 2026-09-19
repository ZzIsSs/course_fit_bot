import React from 'react';
import { Calendar, Flame, CheckCircle2, BookOpen } from 'lucide-react';
import { DashboardStats } from '../../types';

interface MetricCardsProps {
  stats: DashboardStats;
  loading?: boolean;
}

export const MetricCards: React.FC<MetricCardsProps> = ({ stats, loading = false }) => {
  const cards = [
    {
      label: 'Tổng số Deadline',
      value: stats?.total_deadlines ?? 0,
      subtext: `${stats?.pending_deadlines ?? 0} bài đang chờ giải quyết`,
      icon: <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400" />,
      bgIcon: 'bg-blue-50 dark:bg-blue-950/50',
      borderAccent: 'hover:border-blue-300 dark:hover:border-blue-800',
    },
    {
      label: 'Cần nộp gấp (< 24h)',
      value: stats?.urgent_24h ?? 0,
      subtext: (stats?.urgent_24h ?? 0) > 0 ? 'Ưu tiên nộp trước hôm nay' : 'Không có bài gấp',
      icon: <Flame className="w-5 h-5 text-red-600 dark:text-red-400" />,
      bgIcon: 'bg-red-50 dark:bg-red-950/50',
      borderAccent: (stats?.urgent_24h ?? 0) > 0 ? 'border-red-200 dark:border-red-900/50' : '',
    },
    {
      label: 'Đã hoàn thành',
      value: stats?.completed_deadlines ?? 0,
      subtext: `Đạt ${(stats?.completion_rate ?? 0).toFixed(0)}% khối lượng môn`,
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
      bgIcon: 'bg-emerald-50 dark:bg-emerald-950/50',
      borderAccent: 'hover:border-emerald-300 dark:hover:border-emerald-800',
    },
    {
      label: 'Môn học theo dõi',
      value: stats?.total_courses ?? 0,
      subtext: 'Đã liên kết kênh Discord',
      icon: <BookOpen className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />,
      bgIcon: 'bg-indigo-50 dark:bg-indigo-950/50',
      borderAccent: 'hover:border-indigo-300 dark:hover:border-indigo-800',
    },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-28 rounded-xl bg-slate-200 dark:bg-slate-800 animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, i) => (
        <div
          key={i}
          className={`p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm transition-all duration-200 ${card.borderAccent}`}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider truncate pr-2">
              {card.label}
            </span>
            <div className={`p-2 rounded-xl ${card.bgIcon}`}>
              {card.icon}
            </div>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900 dark:text-white">
              {card.value}
            </span>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
            {card.subtext}
          </p>
        </div>
      ))}
    </div>
  );
};
