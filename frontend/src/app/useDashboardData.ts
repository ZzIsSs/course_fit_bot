import { useCallback, useEffect, useState } from 'react';
import { isAbortError } from '@/shared/api/client';
import { AddToast } from '@/shared/hooks/useToasts';
import { useCourses } from '@/features/courses/useCourses';
import { useAnnouncements } from '@/features/announcements/useAnnouncements';
import { useStats } from '@/features/dashboard/useStats';
import { NewDeadlineInput, useDeadlines } from '@/features/deadlines/useDeadlines';

/**
 * Ghép các hook dữ liệu của từng feature và điều phối việc tải chung:
 * một cờ loading / refreshing / fetchError cho cả 4 nguồn (courses, deadlines, stats, announcements).
 * Các feature không import lẫn nhau; việc nối stats với deadlines nằm ở đây.
 */
export function useDashboardData(addToast: AddToast) {
  const { courses, load: loadCourses } = useCourses();
  const { announcements, load: loadAnnouncements } = useAnnouncements();
  const { stats, load: loadStats, applyToggle } = useStats();
  const { deadlines, load: loadDeadlines, toggleComplete, createDeadline } = useDeadlines({
    addToast,
    onOptimisticToggle: applyToggle,
  });

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Load Data with AbortController to prevent memory leaks.
  // Trả về true khi cả 4 request đều thành công. Request nào lỗi thì giữ nguyên
  // dữ liệu cũ của phần đó và hiện banner + toast lỗi.
  const loadData = useCallback(async (signal?: AbortSignal): Promise<boolean> => {
    setFetchError(null);
    try {
      const results = await Promise.allSettled([
        loadCourses(signal),
        loadDeadlines(signal),
        loadStats(signal),
        loadAnnouncements(signal),
      ]);

      const rejected = results.filter((r): r is PromiseRejectedResult => r.status === 'rejected');
      if (rejected.length === 0) return true;
      // Bị hủy (unmount / StrictMode) thì không báo lỗi
      const failure = rejected.find((r) => !isAbortError(r.reason));
      if (!failure) return false;

      const msg = failure.reason instanceof Error ? failure.reason.message : 'Không thể tải dữ liệu từ máy chủ';
      setFetchError(msg);
      addToast('error', msg, 'Lỗi kết nối');
      return false;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast, loadCourses, loadDeadlines, loadStats, loadAnnouncements]);

  // Initial Load
  useEffect(() => {
    const controller = new AbortController();
    loadData(controller.signal);
    return () => controller.abort();
  }, [loadData]);

  // Manual Refresh
  const refresh = async () => {
    setRefreshing(true);
    const ok = await loadData();
    if (ok) {
      addToast('success', 'Dữ liệu đã được làm mới thành công!', 'Đồng bộ hoàn tất');
    }
  };

  // Create Manual Deadline, rồi tải lại toàn bộ dữ liệu
  const createDeadlineAndReload = async (data: NewDeadlineInput): Promise<boolean> => {
    const ok = await createDeadline(data);
    if (ok) {
      await loadData();
    }
    return ok;
  };

  return {
    courses,
    deadlines,
    stats,
    announcements,
    loading,
    refreshing,
    fetchError,
    refresh,
    toggleComplete,
    createDeadline: createDeadlineAndReload,
  };
}
