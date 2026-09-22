import React from 'react';
import { Plus, Sun, Moon, Radio, Menu } from 'lucide-react';
import { Button } from '../ui/Button';
import { getCurrentSemester } from '../../utils/dateUtils';

interface HeaderProps {
  onOpenAddModal: () => void;
  isDarkMode: boolean;
  onToggleTheme: () => void;
  onToggleMobileMenu: () => void;
  semesterLabel?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenAddModal,
  isDarkMode,
  onToggleTheme,
  onToggleMobileMenu,
  semesterLabel,
}) => {
  const currentSemesterLabel = semesterLabel || getCurrentSemester().label;

  return (
    <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-4 sm:px-8 flex items-center justify-between transition-colors">
      {/* Left: Mobile Menu Toggle & Semester Badge */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          aria-label="Mở menu"
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/50">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-500"></span>
            {currentSemesterLabel}
          </span>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50">
            <Radio className="w-3 h-3 text-emerald-500 animate-pulse" />
            <span className="hidden md:inline">Serverless Sync (30m)</span>
            <span className="md:hidden">Live</span>
          </span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        {/* Dark/Light Toggle */}
        <button
          onClick={onToggleTheme}
          aria-label="Đổi giao diện Sáng / Tối"
          className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          {isDarkMode ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* CTA Thêm Deadline */}
        <Button
          size="sm"
          onClick={onOpenAddModal}
          icon={<Plus className="w-4 h-4" />}
          className="shadow-sm font-semibold"
        >
          Thêm Deadline
        </Button>
      </div>
    </header>
  );
};
