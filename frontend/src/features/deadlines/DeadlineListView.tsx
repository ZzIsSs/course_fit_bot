import React from 'react';
import { Deadline } from '../../types';
import { DeadlineItemCard } from './DeadlineItemCard';
import { Skeleton } from '../../components/ui/Skeleton';
import { CheckCircle2, Inbox } from 'lucide-react';
import { getCountdown } from '../../utils/dateUtils';

interface DeadlineListViewProps {
  deadlines: Deadline[];
  loading?: boolean;
  onToggleComplete: (id: number, currentCompleted: boolean) => void;
}

export const DeadlineListView: React.FC<DeadlineListViewProps> = ({
  deadlines = [],
  loading = false,
  onToggleComplete,
}) => {
  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton count={4} className="h-24 w-full" />
      </div>
    );
  }

  if (!deadlines || deadlines.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 text-center rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
          <Inbox className="w-6 h-6" />
        </div>
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
          Không tìm thấy bài tập nào
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mt-1">
          Không có deadline nào phù hợp với bộ lọc hiện tại hoặc bạn đã hoàn thành hết tất cả bài tập.
        </p>
      </div>
    );
  }

  // Phân cụm thời gian
  const urgentList: Deadline[] = [];
  const soonList: Deadline[] = [];
  const normalList: Deadline[] = [];
  const completedList: Deadline[] = [];

  deadlines.forEach((d) => {
    if (d.completed) {
      completedList.push(d);
      return;
    }
    const c = getCountdown(d.due_time);
    if (c.isUrgent) {
      urgentList.push(d);
    } else if (c.diffHours < 72) {
      soonList.push(d);
    } else {
      normalList.push(d);
    }
  });

  return (
    <div className="space-y-6">
      {/* 1. Khẩn cấp (< 24 giờ) */}
      {urgentList.length > 0 && (
        <section className="space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-red-600 dark:text-red-400">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            Khẩn cấp trong 24 giờ ({urgentList.length})
          </div>
          <div className="space-y-2.5">
            {urgentList.map((d) => (
              <DeadlineItemCard
                key={d.deadlines_id}
                deadline={d}
                onToggleComplete={onToggleComplete}
              />
            ))}
          </div>
        </section>
      )}

      {/* 2. Sắp tới (< 3 ngày) */}
      {soonList.length > 0 && (
        <section className="space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            Sắp tới trong 3 ngày ({soonList.length})
          </div>
          <div className="space-y-2.5">
            {soonList.map((d) => (
              <DeadlineItemCard
                key={d.deadlines_id}
                deadline={d}
                onToggleComplete={onToggleComplete}
              />
            ))}
          </div>
        </section>
      )}

      {/* 3. Còn hạn (> 3 ngày) */}
      {normalList.length > 0 && (
        <section className="space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
            Các tuần kế tiếp ({normalList.length})
          </div>
          <div className="space-y-2.5">
            {normalList.map((d) => (
              <DeadlineItemCard
                key={d.deadlines_id}
                deadline={d}
                onToggleComplete={onToggleComplete}
              />
            ))}
          </div>
        </section>
      )}

      {/* 4. Đã hoàn thành */}
      {completedList.length > 0 && (
        <section className="space-y-2.5 pt-2">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Đã hoàn thành ({completedList.length})
          </div>
          <div className="space-y-2.5">
            {completedList.map((d) => (
              <DeadlineItemCard
                key={d.deadlines_id}
                deadline={d}
                onToggleComplete={onToggleComplete}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
