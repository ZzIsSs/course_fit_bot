import { useCallback, useState } from 'react';
import { DashboardStats } from '@/shared/types';
import { getStats } from '@/shared/api/client';

const EMPTY_STATS: DashboardStats = {
  total_deadlines: 0,
  completed_deadlines: 0,
  pending_deadlines: 0,
  completion_rate: 0,
  urgent_24h: 0,
  upcoming_3d: 0,
  overdue: 0,
  total_courses: 0,
};

/** Thống kê Dashboard. `applyToggle` cập nhật tạm thời khi người dùng tick / bỏ tick một deadline. */
export function useStats() {
  const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);

  const load = useCallback(async (signal?: AbortSignal) => {
    setStats(await getStats(signal));
  }, []);

  const applyToggle = useCallback((newCompleted: boolean) => {
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
  }, []);

  return { stats, load, applyToggle };
}
