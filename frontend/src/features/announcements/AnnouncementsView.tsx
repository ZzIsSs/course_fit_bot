import React from 'react';
import { Announcement } from '../../types';
import { Sparkles, ExternalLink, Calendar, User, MessageCircle } from 'lucide-react';
import { formatVietnameseDate } from '../../utils/dateUtils';
import { Skeleton } from '../../components/ui/Skeleton';
import { Badge } from '../../components/ui/Badge';

interface AnnouncementsViewProps {
  announcements: Announcement[];
  loading?: boolean;
}

export const AnnouncementsView: React.FC<AnnouncementsViewProps> = ({
  announcements = [],
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto">
        <Skeleton count={3} className="h-48 w-full" />
      </div>
    );
  }

  // Sample data nếu DB chưa có announcements
  const displayItems = announcements.length > 0 ? announcements : [
    {
      announcements_id: 1,
      courses_id: 1,
      course_name: 'CSC10014',
      announcements_name: 'Thông báo về việc gia hạn nộp bài Lab 2 và dời lịch buổi học phụ đạo',
      source_url: 'https://courses.fit.hcmus.edu.vn',
      created_time: new Date().toISOString(),
      author: 'TS. Trần Minh C (Giảng viên)',
      ai_summary: [
        'Dời hạn nộp Lab 2 thêm 3 ngày: Hạn chót mới là 23:59 Chủ Nhật tuần này.',
        'Lớp phụ đạo chiều Thứ 5 tuần này nghỉ, chuyển sang học bù online tối Thứ 7 lúc 19:30 qua Google Meet.',
        'Sinh viên lưu ý mang theo laptop đã cài sẵn Python 3.12 và thư viện NumPy.',
      ],
    },
    {
      announcements_id: 2,
      courses_id: 2,
      course_name: 'LCN_CQ2024/3',
      announcements_name: 'Khảo sát đăng ký đề cương đồ án tốt nghiệp và xét học bổng khuyến khích kỳ 1',
      source_url: 'https://courses.fit.hcmus.edu.vn',
      created_time: new Date(Date.now() - 86400000).toISOString(),
      author: 'Cố vấn Học tập',
      ai_summary: [
        'Toàn bộ sinh viên bắt buộc hoàn thành biểu mẫu khảo sát trước 17:00 ngày 30/09.',
        'Điều kiện nộp học bổng khuyến khích: Đạt GPA từ 8.0 trở lên và điểm rèn luyện trên 80.',
      ],
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-5 h-5 text-amber-500" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Bảng tin Thông báo & AI Tóm tắt
          </h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Tự động đồng bộ từ diễn đàn Moodle và tạo bản tóm tắt TL;DR bằng Gemini để nắm bắt ý chính trong 3 giây.
        </p>
      </div>

      <div className="space-y-4">
        {displayItems.map((item) => (
          <div
            key={item.announcements_id}
            className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm space-y-4"
          >
            {/* Header: Course + Author + Time */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge variant="course">
                  #{item.course_name?.toLowerCase()}
                </Badge>
                {item.author && (
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300 flex items-center gap-1">
                    <User className="w-3.5 h-3.5 text-slate-400" />
                    {item.author}
                  </span>
                )}
              </div>

              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {formatVietnameseDate(item.created_time)}
              </span>
            </div>

            {/* Original Title */}
            <h3 className="text-base font-bold text-slate-900 dark:text-white leading-snug break-words">
              {item.announcements_name}
            </h3>

            {/* AI Summary Box (Gemini Badge) */}
            {item.ai_summary && item.ai_summary.length > 0 && (
              <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50/70 via-purple-50/50 to-pink-50/30 dark:from-indigo-950/30 dark:via-purple-950/20 dark:to-slate-900 border border-indigo-100 dark:border-indigo-900/50">
                <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-700 dark:text-indigo-300 mb-2">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  <span>AI TL;DR (Tóm tắt bởi Gemini)</span>
                </div>
                <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-200">
                  {item.ai_summary.map((point, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-indigo-500 font-bold shrink-0">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Action Links */}
            <div className="pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-800">
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <MessageCircle className="w-3.5 h-3.5" />
                Diễn đàn thảo luận Moodle
              </span>

              {item.source_url && (
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400 transition-colors"
                >
                  <span>Mở bài gốc trên Moodle</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
