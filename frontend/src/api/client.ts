import { Course, Deadline, DashboardStats, Announcement } from '../types';

const API_BASE = '/api';

/**
 * Helper fetch an toàn với AbortSignal và xử lý lỗi chuẩn mực
 */
async function safeFetch<T>(endpoint: string, options?: RequestInit): Promise<{ ok: boolean; data?: T; error?: string }> {
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
      return { ok: false, error: 'Yêu cầu bị hủy' };
    }
    const message = err instanceof Error ? err.message : 'Không thể kết nối đến máy chủ';
    return { ok: false, error: message };
  }
}

export async function getCourses(signal?: AbortSignal): Promise<Course[]> {
  const res = await safeFetch<{ ok: boolean; data?: Course[] }>('/courses', { signal });
  if (res.ok && Array.isArray(res.data?.data)) {
    return res.data.data;
  }
  return [];
}

export async function getDeadlines(params?: { course?: string; status?: string }, signal?: AbortSignal): Promise<Deadline[]> {
  const query = new URLSearchParams();
  if (params?.course) query.set('course', params.course);
  if (params?.status) query.set('status', params.status);

  const endpoint = `/deadlines${query.toString() ? `?${query.toString()}` : ''}`;
  const res = await safeFetch<{ ok: boolean; data?: Deadline[] }>(endpoint, { signal });
  if (res.ok && Array.isArray(res.data?.data)) {
    return res.data.data;
  }
  return [];
}

export async function getStats(signal?: AbortSignal): Promise<DashboardStats> {
  const res = await safeFetch<{ ok: boolean; data?: DashboardStats }>('/stats', { signal });
  if (res.ok && res.data?.data) {
    return res.data.data;
  }
  return {
    total_deadlines: 0,
    completed_deadlines: 0,
    pending_deadlines: 0,
    completion_rate: 0,
    urgent_24h: 0,
    upcoming_3d: 0,
    overdue: 0,
    total_courses: 0,
  };
}

export async function getAnnouncements(signal?: AbortSignal): Promise<Announcement[]> {
  const res = await safeFetch<{ ok: boolean; data?: Announcement[] }>('/announcements', { signal });
  if (res.ok && Array.isArray(res.data?.data)) {
    return res.data.data;
  }
  return [];
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
