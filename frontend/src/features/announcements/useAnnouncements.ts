import { useCallback, useState } from 'react';
import { Announcement } from '@/shared/types';
import { getAnnouncements } from '@/shared/api/client';

/** Bài đăng diễn đàn Moodle cho tab "Bảng tin". `load` ném lỗi nếu request thất bại. */
export function useAnnouncements() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);

  const load = useCallback(async (signal?: AbortSignal) => {
    setAnnouncements(await getAnnouncements(signal));
  }, []);

  return { announcements, load };
}
