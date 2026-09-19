import React from 'react';
import {
  LayoutDashboard,
  CalendarCheck2,
  BookOpen,
  Sparkles,
  Settings,
  GraduationCap,
  X,
} from 'lucide-react';
import { ActiveTab } from '../../types';

interface SidebarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isMobileOpen,
  onCloseMobile,
}) => {
  const navItems: { id: ActiveTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    {
      id: 'overview',
      label: 'Tổng quan',
      icon: <LayoutDashboard className="w-4 h-4 shrink-0" />,
    },
    {
      id: 'deadlines',
      label: 'Quản lý Deadline',
      icon: <CalendarCheck2 className="w-4 h-4 shrink-0" />,
    },
    {
      id: 'courses',
      label: 'Môn học & Tài liệu',
      icon: <BookOpen className="w-4 h-4 shrink-0" />,
    },
    {
      id: 'announcements',
      label: 'Bảng tin & AI',
      icon: <Sparkles className="w-4 h-4 shrink-0 text-amber-500" />,
      badge: 'Gemini',
    },
    {
      id: 'settings',
      label: 'Cài đặt & Đồng bộ',
      icon: <Settings className="w-4 h-4 shrink-0" />,
    },
  ];

  const handleNavClick = (tab: ActiveTab) => {
    onSelectTab(tab);
    onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="lg:hidden fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col justify-between transition-transform duration-200 lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Branding */}
        <div>
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-700 to-blue-500 flex items-center justify-center text-white shadow-md shadow-brand-500/20">
                <GraduationCap className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
                  Course FIT
                </h1>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                  HCMUS Study Hub
                </p>
              </div>
            </div>

            <button
              onClick={onCloseMobile}
              aria-label="Đóng menu"
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1.5">
            <div className="px-3 pb-2 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Không gian học tập
            </div>

            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 font-semibold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {item.icon}
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-xs">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Profile / Version info */}
        <div className="p-4 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center justify-between px-2 py-1 text-xs text-slate-400 dark:text-slate-500">
            <span>Phiên bản bot</span>
            <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              v2.0-serverless
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
