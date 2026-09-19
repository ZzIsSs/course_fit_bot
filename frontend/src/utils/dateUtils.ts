/**
 * Date utility functions with defensive error-handling.
 * Luôn đảm bảo không crash ứng dụng nếu dữ liệu ngày sai lệch.
 */

export function parseSafeDate(dateInput?: string | number | Date | null): Date | null {
  if (!dateInput) return null;
  try {
    const d = new Date(dateInput);
    if (isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

export function formatVietnameseDate(dateInput?: string | number | Date | null): string {
  const d = parseSafeDate(dateInput);
  if (!d) return 'Chưa xác định';

  try {
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();

    return `${hours}:${minutes} ${day}/${month}/${year}`;
  } catch {
    return 'Chưa xác định';
  }
}

export function getCountdown(dateInput?: string | number | Date | null): {
  text: string;
  isUrgent: boolean;
  isOverdue: boolean;
  diffHours: number;
} {
  const target = parseSafeDate(dateInput);
  if (!target) {
    return { text: 'Không rõ thời hạn', isUrgent: false, isOverdue: false, diffHours: 9999 };
  }

  const now = new Date();
  const diffMs = target.getTime() - now.getTime();
  const diffHours = diffMs / (1000 * 60 * 60);

  if (diffMs < 0) {
    const pastHours = Math.abs(diffHours);
    if (pastHours < 24) {
      return {
        text: `Quá hạn ${Math.floor(pastHours)} giờ trước`,
        isUrgent: false,
        isOverdue: true,
        diffHours,
      };
    }
    const pastDays = Math.floor(pastHours / 24);
    return {
      text: `Quá hạn ${pastDays} ngày trước`,
      isUrgent: false,
      isOverdue: true,
      diffHours,
    };
  }

  // Còn hạn
  if (diffHours < 24) {
    const h = Math.floor(diffHours);
    const m = Math.floor((diffHours - h) * 60);
    return {
      text: h > 0 ? `Còn ${h} giờ ${m} phút` : `Còn ${m} phút`,
      isUrgent: true,
      isOverdue: false,
      diffHours,
    };
  }

  const days = Math.floor(diffHours / 24);
  const remainHours = Math.floor(diffHours % 24);
  return {
    text: remainHours > 0 ? `Còn ${days} ngày ${remainHours} giờ` : `Còn ${days} ngày`,
    isUrgent: days < 3,
    isOverdue: false,
    diffHours,
  };
}
