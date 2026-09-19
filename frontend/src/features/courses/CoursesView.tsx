import React, { useState } from 'react';
import { Course } from '../../types';
import { BookOpen, MessageSquare, ExternalLink, Search, Layers } from 'lucide-react';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';

interface CoursesViewProps {
  courses: Course[];
  loading?: boolean;
}

export const CoursesView: React.FC<CoursesViewProps> = ({ courses = [], loading = false }) => {
  const [search, setSearch] = useState('');

  const filtered = courses.filter((c) => {
    const q = search.toLowerCase();
    const nameMatch = c.course_name?.toLowerCase().includes(q);
    const displayMatch = c.display_name?.toLowerCase().includes(q);
    return nameMatch || displayMatch;
  });

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Skeleton count={6} className="h-44 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Danh mục Môn học & Kênh Discord
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Tổng cộng {courses.length} môn học đã được bot quét và tạo kênh thảo luận theo chuẩn format.
          </p>
        </div>

        <div className="relative max-w-xs w-full">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo mã môn hoặc tên..."
            className="w-full h-10 pl-9 pr-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* Grid of Course Cards */}
      {filtered.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-500 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800">
          Không tìm thấy môn học nào phù hợp với từ khóa "{search}".
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((course) => {
            const moodleUrl = course.lms_courses_id
              ? `https://courses.fit.hcmus.edu.vn/course/view.php?id=${course.lms_courses_id}`
              : null;

            return (
              <div
                key={course.courses_id}
                className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="font-mono text-xs font-bold px-2.5 py-1 rounded-lg bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/40">
                      {course.course_name}
                    </span>

                    {course.pending_deadlines_count ? (
                      <Badge variant="urgent">
                        {course.pending_deadlines_count} bài mở
                      </Badge>
                    ) : (
                      <span className="text-[11px] text-slate-400">
                        LMS ID: {course.lms_courses_id}
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-slate-900 dark:text-white line-clamp-2 leading-snug mb-2">
                    {course.display_name || course.course_name}
                  </h3>
                </div>

                <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400 truncate max-w-[180px]">
                    <Layers className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">#{course.course_name.toLowerCase()}</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {course.chat_id && (
                      <a
                        href={`discord://discord.com/channels/@me/${course.chat_id}`}
                        title="Mở kênh Discord môn học"
                        className="p-1.5 rounded-lg text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </a>
                    )}
                    {moodleUrl && (
                      <a
                        href={moodleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Mở trang Moodle môn học"
                        className="p-1.5 rounded-lg text-slate-500 hover:text-brand-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
