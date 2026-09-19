import React from 'react';
import { Search, Filter, List, LayoutGrid, X } from 'lucide-react';
import { Course, FilterStatus, ViewMode } from '../../types';

interface DeadlineToolbarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedCourse: string;
  onCourseChange: (c: string) => void;
  courses: Course[];
  filterStatus: FilterStatus;
  onFilterStatusChange: (status: FilterStatus) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  counts: {
    all: number;
    pending: number;
    urgent: number;
    completed: number;
    overdue: number;
  };
}

export const DeadlineToolbar: React.FC<DeadlineToolbarProps> = ({
  searchQuery,
  onSearchChange,
  selectedCourse,
  onCourseChange,
  courses = [],
  filterStatus,
  onFilterStatusChange,
  viewMode,
  onViewModeChange,
  counts,
}) => {
  const filterTabs: { id: FilterStatus; label: string; count: number }[] = [
    { id: 'all', label: 'Tất cả', count: counts.all },
    { id: 'pending', label: 'Chưa xong', count: counts.pending },
    { id: 'urgent', label: 'Khẩn cấp (<24h)', count: counts.urgent },
    { id: 'completed', label: 'Đã nộp', count: counts.completed },
    { id: 'overdue', label: 'Quá hạn', count: counts.overdue },
  ];

  return (
    <div className="space-y-4">
      {/* Top row: Search, Course Dropdown & View Mode Switcher */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="flex flex-1 items-center gap-3">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Tìm theo tên bài tập hoặc mã môn..."
              className="w-full h-10 pl-9 pr-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all shadow-xs"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Course Filter Dropdown */}
          <div className="relative">
            <select
              value={selectedCourse}
              onChange={(e) => onCourseChange(e.target.value)}
              className="h-10 px-3 pr-8 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 shadow-xs appearance-none cursor-pointer"
            >
              <option value="">Tất cả môn học</option>
              {courses.map((c) => (
                <option key={c.courses_id} value={c.course_name}>
                  {c.course_name} {c.display_name ? `- ${c.display_name}` : ''}
                </option>
              ))}
            </select>
            <Filter className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>
        </div>

        {/* View Switcher: List vs Kanban */}
        <div className="flex items-center p-1 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700/60 self-end sm:self-auto">
          <button
            onClick={() => onViewModeChange('list')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewMode === 'list'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <List className="w-3.5 h-3.5" />
            <span>Danh sách</span>
          </button>
          <button
            onClick={() => onViewModeChange('kanban')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewMode === 'kanban'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span>Kanban</span>
          </button>
        </div>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {filterTabs.map((tab) => {
          const isActive = filterStatus === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onFilterStatusChange(tab.id)}
              className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                isActive
                  ? 'bg-brand-600 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
