import React from 'react';
import {
  LayoutDashboard,
  CalendarCheck2,
  BookOpen,
  Sparkles,
  Settings,
  Plus,
} from 'lucide-react';
import { ActiveTab } from '@/shared/types';

interface BottomNavProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  onOpenAddModal: () => void;
  urgentCount?: number;
}

export const BottomNav: React.FC<BottomNavProps> = ({
  activeTab,
  onSelectTab,
  onOpenAddModal,
  urgentCount = 0,
}) => {
  const tabs: { id: ActiveTab; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: 'overview',
      label: 'Tổng quan',
      icon: <LayoutDashboard className="w-5 h-5" />,
    },
    {
      id: 'deadlines',
      label: 'Deadline',
      icon: <CalendarCheck2 className="w-5 h-5" />,
      badge: urgentCount > 0 ? urgentCount : undefined,
    },
    {
      id: 'courses',
      label: 'Môn học',
      icon: <BookOpen className="w-5 h-5" />,
    },
    {
      id: 'announcements',
      label: 'Bảng tin',
      icon: <Sparkles className="w-5 h-5" />,
    },
    {
      id: 'settings',
      label: 'Cài đặt',
      icon: <Settings className="w-5 h-5" />,
    },
  ];

  return (
    <>
      {/* Floating Action Button for Mobile (Bottom Right) */}
      <button
        onClick={onOpenAddModal}
        aria-label="Thêm Deadline Nhanh"
        className="lg:hidden fixed right-4 bottom-20 z-30 w-14 h-14 rounded-full bg-gradient-to-tr from-brand-600 to-blue-500 hover:from-brand-700 hover:to-blue-600 text-white shadow-lg shadow-brand-500/40 flex items-center justify-center transition-transform active:scale-95 focus:outline-none focus:ring-4 focus:ring-brand-500/30"
      >
        <Plus className="w-7 h-7 stroke-[2.5]" />
      </button>

      {/* Bottom Navigation Bar */}
      <nav
        aria-label="Điều hướng chính trên điện thoại"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-30 h-16 bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg border-t border-slate-200/80 dark:border-slate-800/80 px-2 flex items-center justify-around safe-area-inset-bottom"
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`relative flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all duration-150 ${
                isActive
                  ? 'text-brand-600 dark:text-brand-400 font-bold'
                  : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 font-medium'
              }`}
            >
              <div className="relative">
                {tab.icon}
                {tab.badge !== undefined && (
                  <span className="absolute -top-1.5 -right-2 min-w-4 h-4 px-1 rounded-full bg-rose-500 text-[10px] font-bold text-white flex items-center justify-center animate-pulse">
                    {tab.badge > 9 ? '9+' : tab.badge}
                  </span>
                )}
              </div>
              <span className="text-[10px] mt-1 tracking-tight">{tab.label}</span>
              {isActive && (
                <span className="absolute bottom-0 w-6 h-0.5 rounded-full bg-brand-600 dark:bg-brand-400" />
              )}
            </button>
          );
        })}
      </nav>
    </>
  );
};
