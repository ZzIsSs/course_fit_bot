import { useMemo, useState } from 'react';
import { Deadline, FilterStatus } from '@/shared/types';
import { getCountdown } from '@/shared/utils/dateUtils';

/** Tìm kiếm + lọc theo môn và trạng thái, kèm số lượng cho từng tab trạng thái. */
export function useDeadlineFilters(deadlines: Deadline[]) {
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCourse, setSelectedCourse] = useState('');

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

  return {
    filterStatus,
    setFilterStatus,
    searchQuery,
    setSearchQuery,
    selectedCourse,
    setSelectedCourse,
    filteredDeadlines,
    counts,
  };
}
