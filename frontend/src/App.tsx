import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ActiveTab, ViewMode, FilterStatus, Deadline, Course, DashboardStats, Announcement, ToastMessage } from './types';
import { getCourses, getDeadlines, getStats, getAnnouncements, createManualDeadline, toggleDeadlineCompletion } from './api/client';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ToastContainer } from './components/ui/Toast';
import { HeroProgressBanner } from './features/dashboard/HeroProgressBanner';
import { MetricCards } from './features/dashboard/MetricCards';
import { DeadlineToolbar } from './features/deadlines/DeadlineToolbar';
import { DeadlineListView } from './features/deadlines/DeadlineListView';
import { DeadlineKanbanView } from './features/deadlines/DeadlineKanbanView';
import { AddDeadlineModal } from './features/deadlines/AddDeadlineModal';
import { CoursesView } from './features/courses/CoursesView';
import { AnnouncementsView } from './features/announcements/AnnouncementsView';
import { SettingsView } from './features/settings/SettingsView';
import { getCountdown } from './utils/dateUtils';
import { Calendar, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from './components/ui/Button';

export const App: React.FC = () => {
  // Navigation & View States
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCourse, setSelectedCourse] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Theme State
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('course_fit_theme');
      if (saved) return saved === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch {
      return false;
    }
  });

  // Data States
  const [courses, setCourses] = useState<Course[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [stats, setStats] = useState<DashboardStats>({
    total_deadlines: 0,
    completed_deadlines: 0,
    pending_deadlines: 0,
    completion_rate: 0,
    urgent_24h: 0,
    upcoming_3d: 0,
    overdue: 0,
    total_courses: 0,
  });
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Toast State
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((type: 'success' | 'error' | 'info' | 'warning', message: string, title?: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, message, title }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Sync Dark mode with DOM
  useEffect(() => {
    try {
      if (isDarkMode) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('course_fit_theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('course_fit_theme', 'light');
      }
    } catch {
      // Ignored in strict security environments
    }
  }, [isDarkMode]);

  const toggleTheme = () => setIsDarkMode((prev) => !prev);

  // Load Data with AbortController to prevent memory leaks
  const loadData = useCallback(async (signal?: AbortSignal) => {
    setFetchError(null);
    try {
      const [coursesData, deadlinesData, statsData, announcementsData] = await Promise.allSettled([
        getCourses(signal),
        getDeadlines(undefined, signal),
        getStats(signal),
        getAnnouncements(signal),
      ]);

      if (coursesData.status === 'fulfilled') setCourses(coursesData.value ?? []);
      if (deadlinesData.status === 'fulfilled') setDeadlines(deadlinesData.value ?? []);
      if (statsData.status === 'fulfilled') setStats(statsData.value);
      if (announcementsData.status === 'fulfilled') setAnnouncements(announcementsData.value ?? []);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const msg = err instanceof Error ? err.message : 'Không thể tải dữ liệu từ máy chủ';
      setFetchError(msg);
      addToast('error', msg, 'Lỗi kết nối');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  // Initial Load
  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  // Manual Refresh
  const handleManualRefresh = async () => {
    setRefreshing(true);
    await loadData();
    addToast('success', 'Dữ liệu đã được làm mới thành công!', 'Đồng bộ hoàn tất');
  };

  // Optimistic Toggle Complete (0ms latency!)
  const handleToggleComplete = async (id: number, currentCompleted: boolean) => {
    const target = deadlines.find((d) => d.deadlines_id === id);
    if (!target) return;

    const newCompleted = !currentCompleted;

    // 1. Optimistic Update UI ngay lập tức
    setDeadlines((prev) =>
      prev.map((d) =>
        d.deadlines_id === id
          ? {
              ...d,
              completed: newCompleted,
              completed_by: newCompleted ? 'Bạn' : null,
            }
          : d
      )
    );

    // Cập nhật stats tạm thời
    setStats((prev) => {
      const completedCount = newCompleted ? prev.completed_deadlines + 1 : Math.max(0, prev.completed_deadlines - 1);
      const pendingCount = newCompleted ? Math.max(0, prev.pending_deadlines - 1) : prev.pending_deadlines + 1;
      const rate = prev.total_deadlines > 0 ? (completedCount / prev.total_deadlines) * 100 : 0;
      return {
        ...prev,
        completed_deadlines: completedCount,
        pending_deadlines: pendingCount,
        completion_rate: rate,
      };
    });

    // 2. Gửi request Backend ngầm
    const result = await toggleDeadlineCompletion(id, newCompleted);

    if (!result.ok) {
      // 3. Rollback nếu có lỗi mạng
      setDeadlines((prev) =>
        prev.map((d) =>
          d.deadlines_id === id
            ? { ...d, completed: currentCompleted, completed_by: target.completed_by }
            : d
        )
      );
      addToast('error', result.error || 'Không thể đồng bộ trạng thái lên cơ sở dữ liệu', 'Lỗi cập nhật');
    } else {
      addToast(
        'success',
        newCompleted
          ? `Đã hoàn thành "${target.deadline_name}". Lịch Google & Notion đã được cập nhật!`
          : `Đã mở lại "${target.deadline_name}".`,
        newCompleted ? 'Hoàn tất bài tập ✅' : 'Đã cập nhật'
      );
    }
  };

  // Create Manual Deadline
  const handleCreateDeadline = async (data: {
    mon: string;
    ten: string;
    han_chot: string;
    nguoi_phu_trach?: string;
    ghi_chu_url?: string;
  }): Promise<boolean> => {
    const res = await createManualDeadline(data);
    if (!res.ok) {
      addToast('error', res.error || 'Lỗi khi tạo deadline', 'Thất bại');
      return false;
    }

    addToast('success', `Đã thêm deadline "${data.ten}". Bot sẽ tự động thông báo trên Discord!`, 'Thành công 🎉');
    await loadData();
    return true;
  };

  // Filtered Deadlines
  const filteredDeadlines = useMemo(() => {
    return (deadlines ?? []).filter((d) => {
      // 1. Lọc theo search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = d.deadline_name?.toLowerCase().includes(q);
        const matchCourse = d.course_name?.toLowerCase().includes(q);
        if (!matchName && !matchCourse) return false;
      }

      // 2. Lọc theo Course
      if (selectedCourse && d.course_name !== selectedCourse) {
        return false;
      }

      // 3. Lọc theo Status
      const countdown = getCountdown(d.due_time);
      switch (filterStatus) {
        case 'pending':
          return !d.completed;
        case 'urgent':
          return !d.completed && countdown.isUrgent;
        case 'completed':
          return d.completed;
        case 'overdue':
          return !d.completed && countdown.isOverdue;
        case 'all':
        default:
          return true;
      }
    });
  }, [deadlines, searchQuery, selectedCourse, filterStatus]);

  // Counts for tabs
  const counts = useMemo(() => {
    let pending = 0;
    let urgent = 0;
    let completed = 0;
    let overdue = 0;

    (deadlines ?? []).forEach((d) => {
      if (d.completed) {
        completed++;
      } else {
        pending++;
        const c = getCountdown(d.due_time);
        if (c.isOverdue) overdue++;
        else if (c.isUrgent) urgent++;
      }
    });

    return {
      all: deadlines.length,
      pending,
      urgent,
      completed,
      overdue,
    };
  }, [deadlines]);

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
        <main className="flex-1 p-4 sm:p-8 max-w-7xl w-full mx-auto space-y-8">
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
    </div>
  );
};
export default App;
