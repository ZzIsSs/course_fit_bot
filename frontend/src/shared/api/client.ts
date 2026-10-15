import { Course, Deadline, DashboardStats, Announcement } from '@/shared/types';

const API_BASE = '/api';

/**
 * Helper fetch an toàn với AbortSignal và xử lý lỗi chuẩn mực
 */
async function safeFetch<T>(endpoint: string, options?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string; aborted?: boolean }> {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      return {
        ok: false,
        error: errJson?.error ?? `Lỗi máy chủ HTTP ${res.status}: ${res.statusText}`,
      };
    }

    const data = await res.json();
    return { ok: true, data };
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      return { ok: false, error: 'Yêu cầu bị hủy', aborted: true };
    }
    const message = err instanceof Error ? err.message : 'Không thể kết nối đến máy chủ';
    return { ok: false, error: message };
  }
}

/** Kiểm tra request bị hủy (AbortController) — không phải lỗi cần báo cho người dùng. */
export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

/**
 * Lấy `data` từ response dạng { ok, data }. Ném lỗi khi request thất bại thay vì
 * trả về mảng rỗng, để giao diện biết là lỗi kết nối chứ không phải "không có dữ liệu".
 */
async function fetchData<T>(endpoint: string, signal: AbortSignal | undefined, isValid: (data: unknown) => boolean): Promise<T> {
  const res = await safeFetch<{ ok: boolean; data?: T }>(endpoint, { signal });
  if (res.aborted) {
    throw new DOMException('Yêu cầu bị hủy', 'AbortError');
  }
  if (!res.ok) {
    throw new Error(res.error ?? 'Không thể tải dữ liệu từ máy chủ');
  }
  if (!isValid(res.data?.data)) {
    throw new Error(`Dữ liệu trả về từ ${endpoint} không đúng định dạng`);
  }
  return res.data!.data as T;
}

export async function getCourses(signal?: AbortSignal): Promise<Course[]> {
  return fetchData<Course[]>('/courses', signal, Array.isArray);
}

export async function getDeadlines(params?: { course?: string; status?: string }, signal?: AbortSignal): Promise<Deadline[]> {
  const query = new URLSearchParams();
  if (params?.course) query.set('course', params.course);
  if (params?.status) query.set('status', params.status);

  const endpoint = `/deadlines${query.toString() ? `?${query.toString()}` : ''}`;
  return fetchData<Deadline[]>(endpoint, signal, Array.isArray);
}

export async function getStats(signal?: AbortSignal): Promise<DashboardStats> {
  return fetchData<DashboardStats>('/stats', signal, (d) => typeof d === 'object' && d !== null);
}

export async function getAnnouncements(signal?: AbortSignal): Promise<Announcement[]> {
  return fetchData<Announcement[]>('/announcements', signal, Array.isArray);
}

export async function createManualDeadline(payload: {
  mon: string;
  ten: string;
  han_chot: string;
  nguoi_phu_trach?: string;
  ghi_chu_url?: string;
}): Promise<{ ok: boolean; deadlines_id?: number; error?: string }> {
  const res = await safeFetch<{ ok: boolean; deadlines_id?: number; error?: string }>('/deadlines', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (res.ok && res.data?.ok) {
    return { ok: true, deadlines_id: res.data.deadlines_id };
  }
  return { ok: false, error: res.error || res.data?.error || 'Không thể tạo deadline' };
}

export async function toggleDeadlineCompletion(
  id: number,
  completed: boolean,
  completedBy: string = 'Bạn'
): Promise<{ ok: boolean; error?: string }> {
  const res = await safeFetch<{ ok: boolean; error?: string }>('/deadlines/toggle', {
    method: 'POST',
    body: JSON.stringify({
      deadlines_id: id,
      completed,
      completed_by: completedBy,
    }),
  });
  if (res.ok && res.data?.ok) {
    return { ok: true };
  }
  return { ok: false, error: res.error || res.data?.error || 'Không thể cập nhật trạng thái' };
}
