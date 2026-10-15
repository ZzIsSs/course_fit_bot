import { useCallback, useState } from 'react';
import { Deadline } from '@/shared/types';
import { createManualDeadline, getDeadlines, toggleDeadlineCompletion } from '@/shared/api/client';
import { AddToast } from '@/shared/hooks/useToasts';

export interface NewDeadlineInput {
  mon: string;
  ten: string;
  han_chot: string;
  nguoi_phu_trach?: string;
  ghi_chu_url?: string;
}

interface UseDeadlinesOptions {
  addToast: AddToast;
  /** Gọi ngay khi tick / bỏ tick (trước khi server trả lời), ví dụ để cập nhật stats tạm thời. */
  onOptimisticToggle?: (newCompleted: boolean) => void;
}

/** Danh sách deadline: tải, tick hoàn thành kiểu optimistic (có rollback) và tạo deadline thủ công. */
export function useDeadlines({ addToast, onOptimisticToggle }: UseDeadlinesOptions) {
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);

  const load = useCallback(async (signal?: AbortSignal) => {
    setDeadlines(await getDeadlines(undefined, signal));
  }, []);

  // Optimistic Toggle Complete (0ms latency!)
  const toggleComplete = async (id: number, currentCompleted: boolean) => {
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
    onOptimisticToggle?.(newCompleted);

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

  /** Tạo deadline thủ công. Trả về true nếu thành công (người gọi tự tải lại dữ liệu). */
  const createDeadline = async (data: NewDeadlineInput): Promise<boolean> => {
    const res = await createManualDeadline(data);
    if (!res.ok) {
      addToast('error', res.error || 'Lỗi khi tạo deadline', 'Thất bại');
      return false;
    }

    addToast('success', `Đã thêm deadline "${data.ten}". Bot sẽ tự động thông báo trên Discord!`, 'Thành công 🎉');
    return true;
  };

  return { deadlines, load, toggleComplete, createDeadline };
}
