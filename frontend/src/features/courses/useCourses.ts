import { useCallback, useState } from 'react';
import { Course } from '@/shared/types';
import { getCourses } from '@/shared/api/client';

/** Danh sách môn học. `load` ném lỗi nếu request thất bại (giữ nguyên dữ liệu cũ). */
export function useCourses() {
  const [courses, setCourses] = useState<Course[]>([]);

  const load = useCallback(async (signal?: AbortSignal) => {
    setCourses(await getCourses(signal));
  }, []);

  return { courses, load };
}
