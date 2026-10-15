import React, { useState } from 'react';
import { ActiveTab, ViewMode } from '@/shared/types';
import { useToasts } from '@/shared/hooks/useToasts';
import { useTheme } from '@/app/useTheme';
import { useDashboardData } from '@/app/useDashboardData';
import { useDeadlineFilters } from '@/features/deadlines/useDeadlineFilters';
import { Header } from '@/app/layout/Header';
import { Sidebar } from '@/app/layout/Sidebar';
import { BottomNav } from '@/app/layout/BottomNav';
import { ToastContainer } from '@/shared/ui/Toast';
import { HeroProgressBanner } from '@/features/dashboard/HeroProgressBanner';
import { MetricCards } from '@/features/dashboard/MetricCards';
import { DeadlineToolbar } from '@/features/deadlines/DeadlineToolbar';
import { DeadlineListView } from '@/features/deadlines/DeadlineListView';
import { DeadlineKanbanView } from '@/features/deadlines/DeadlineKanbanView';
import { AddDeadlineModal } from '@/features/deadlines/AddDeadlineModal';
import { CoursesView } from '@/features/courses/CoursesView';
import { AnnouncementsView } from '@/features/announcements/AnnouncementsView';
import { SettingsView } from '@/features/settings/SettingsView';
import { Calendar, AlertCircle } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

export const App: React.FC = () => {
  // Navigation & View States
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  const { toasts, addToast, dismissToast } = useToasts();
  const { isDarkMode, toggleTheme } = useTheme();
  const {
    courses,
    deadlines,
    stats,
    announcements,
    loading,
    refreshing,
    fetchError,
    refresh: handleManualRefresh,
    toggleComplete: handleToggleComplete,
    createDeadline: handleCreateDeadline,
  } = useDashboardData(addToast);
  const {
    filterStatus,
    setFilterStatus,
    searchQuery,
    setSearchQuery,
    selectedCourse,
    setSelectedCourse,
    filteredDeadlines,
    counts,
  } = useDeadlineFilters(deadlines);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-canvas-dark text-slate-900 dark:text-slate-100 transition-colors">
      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Sidebar (Desktop + Mobile Drawer) */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <Header
          semesterLabel={stats.semester?.label}
          onOpenAddModal={() => setIsAddModalOpen(true)}
          isDarkMode={isDarkMode}
          onToggleTheme={toggleTheme}
          onToggleMobileMenu={() => setIsMobileSidebarOpen(true)}
        />

        {/* Page Body */}
        <main className="flex-1 p-4 sm:p-8 pb-28 lg:pb-8 max-w-7xl w-full mx-auto space-y-8">
          {fetchError && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 flex items-center justify-between gap-3 text-xs text-amber-800 dark:text-amber-200">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>{fetchError}. Đang sử dụng dữ liệu cục bộ.</span>
              </div>
              <Button size="sm" variant="outline" onClick={handleManualRefresh} loading={refreshing}>
                Thử lại
              </Button>
            </div>
          )}

          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-8">
              {/* Hero Banner */}
              <HeroProgressBanner
                completionRate={stats.completion_rate}
                completedCount={stats.completed_deadlines}
                totalCount={stats.total_deadlines}
                semesterLabel={stats.semester?.label}
                onViewAllDeadlines={() => {
                  setActiveTab('deadlines');
                  setFilterStatus('all');
                }}
              />

              {/* 4 Metric KPI Cards */}
              <MetricCards stats={stats} loading={loading} />

              {/* Deadlines cần chú ý */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-brand-600" />
                    Bài tập sắp đến hạn
                  </h3>
                  <button
                    onClick={() => setActiveTab('deadlines')}
                    className="text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400"
                  >
                    Xem tất cả ({deadlines.length}) →
                  </button>
                </div>

                <DeadlineListView
                  deadlines={deadlines.filter((d) => !d.completed).slice(0, 5)}
                  loading={loading}
                  onToggleComplete={handleToggleComplete}
                />
              </div>
            </div>
          )}

          {/* TAB 2: DEADLINES HUB */}
          {activeTab === 'deadlines' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  Trung tâm Quản lý Deadline
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Tra cứu, lọc và đánh dấu hoàn thành bài tập theo thời gian thực.
                </p>
              </div>

              {/* Toolbar */}
              <DeadlineToolbar
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                selectedCourse={selectedCourse}
                onCourseChange={setSelectedCourse}
                courses={courses}
                filterStatus={filterStatus}
                onFilterStatusChange={setFilterStatus}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                counts={counts}
              />

              {/* List View vs Kanban View */}
              {viewMode === 'list' ? (
                <DeadlineListView
                  deadlines={filteredDeadlines}
                  loading={loading}
                  onToggleComplete={handleToggleComplete}
                />
              ) : (
                <DeadlineKanbanView
                  deadlines={filteredDeadlines}
                  onToggleComplete={handleToggleComplete}
                />
              )}
            </div>
          )}

          {/* TAB 3: COURSES & MATERIALS */}
          {activeTab === 'courses' && (
            <CoursesView courses={courses} loading={loading} />
          )}

          {/* TAB 4: ANNOUNCEMENTS & AI */}
          {activeTab === 'announcements' && (
            <AnnouncementsView announcements={announcements} loading={loading} />
          )}

          {/* TAB 5: SETTINGS */}
          {activeTab === 'settings' && (
            <SettingsView
              onManualRefresh={handleManualRefresh}
              refreshing={refreshing}
            />
          )}
        </main>
      </div>

      {/* Quick Add Deadline Modal */}
      <AddDeadlineModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        courses={courses}
        onSubmit={handleCreateDeadline}
      />

      {/* Mobile Bottom Navigation & Quick Action */}
      <BottomNav
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenAddModal={() => setIsAddModalOpen(true)}
        urgentCount={stats.urgent_24h}
      />
    </div>
  );
};
export default App;
