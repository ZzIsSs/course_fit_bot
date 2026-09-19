import React, { useState } from 'react';
import { Course } from '../../types';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import { Calendar, User, Link as LinkIcon, Sparkles } from 'lucide-react';

interface AddDeadlineModalProps {
  isOpen: boolean;
  onClose: () => void;
  courses: Course[];
  onSubmit: (data: {
    mon: string;
    ten: string;
    han_chot: string;
    nguoi_phu_trach?: string;
    ghi_chu_url?: string;
  }) => Promise<boolean>;
}

export const AddDeadlineModal: React.FC<AddDeadlineModalProps> = ({
  isOpen,
  onClose,
  courses = [],
  onSubmit,
}) => {
  const [courseCode, setCourseCode] = useState('');
  const [title, setTitle] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [dueTime, setDueTime] = useState('23:59');
  const [assignee, setAssignee] = useState('');
  const [notesUrl, setNotesUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Helper đặt nhanh ngày giờ
  const setQuickDate = (daysAhead: number) => {
    const d = new Date();
    d.setDate(d.getDate() + daysAhead);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    setDueDate(`${year}-${month}-${day}`);
    setDueTime('23:59');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    // Defensive: Kiểm tra dữ liệu đầu vào
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setErrorMessage('Vui lòng nhập tên bài tập / mốc deadline.');
      return;
    }

    const selectedCourse = courseCode || (courses[0]?.course_name ?? '');
    if (!selectedCourse) {
      setErrorMessage('Vui lòng chọn môn học liên quan.');
      return;
    }

    if (!dueDate) {
      setErrorMessage('Vui lòng chọn ngày hết hạn.');
      return;
    }

    // Format ngày giờ: dd/mm/yyyy HH:MM
    const [year, month, day] = dueDate.split('-');
    const formattedDue = `${day}/${month}/${year} ${dueTime || '23:59'}`;

    setSubmitting(true);
    try {
      const success = await onSubmit({
        mon: selectedCourse,
        ten: trimmedTitle,
        han_chot: formattedDue,
        nguoi_phu_trach: assignee.trim() || undefined,
        ghi_chu_url: notesUrl.trim() || undefined,
      });

      if (success) {
        // Reset form
        setTitle('');
        setAssignee('');
        setNotesUrl('');
        setDueDate('');
        onClose();
      }
    } catch {
      setErrorMessage('Đã xảy ra lỗi khi tạo deadline. Vui lòng thử lại.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Thêm Mốc Deadline Mới">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && (
          <div className="p-3 rounded-xl text-xs bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
            {errorMessage}
          </div>
        )}

        {/* Môn học */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Môn học <span className="text-red-500">*</span>
          </label>
          <select
            value={courseCode}
            onChange={(e) => setCourseCode(e.target.value)}
            required
            className="w-full h-10 px-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="" disabled>-- Chọn môn học --</option>
            {courses.map((c) => (
              <option key={c.courses_id} value={c.course_name}>
                {c.course_name} {c.display_name ? `- ${c.display_name}` : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Tên bài tập */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Tên công việc / Bài tập <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="VD: Nộp báo cáo giữa kỳ Đồ án"
            required
            maxLength={250}
            className="w-full h-10 px-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Hạn chót & Nút chọn nhanh */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Hạn chót <span className="text-red-500">*</span>
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
            <div className="relative">
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                required
                className="w-full h-10 px-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="relative">
              <input
                type="time"
                value={dueTime}
                onChange={(e) => setDueTime(e.target.value)}
                required
                className="w-full h-10 px-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          {/* Quick shortcuts */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-500" />
              Nhanh:
            </span>
            <button
              type="button"
              onClick={() => setQuickDate(0)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-600 dark:text-slate-300 transition-colors"
            >
              Hôm nay 23:59
            </button>
            <button
              type="button"
              onClick={() => setQuickDate(1)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-600 dark:text-slate-300 transition-colors"
            >
              Tối mai 23:59
            </button>
            <button
              type="button"
              onClick={() => setQuickDate(3)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-600 dark:text-slate-300 transition-colors"
            >
              +3 ngày nữa
            </button>
          </div>
        </div>

        {/* Người phụ trách */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Người phụ trách / Tag thành viên
          </label>
          <div className="relative">
            <User className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              placeholder="VD: @BaoNguyen hoặc Nhóm 4"
              className="w-full h-10 pl-9 pr-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Link ghi chú */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
            Link tài liệu / Ghi chú
          </label>
          <div className="relative">
            <LinkIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="url"
              value={notesUrl}
              onChange={(e) => setNotesUrl(e.target.value)}
              placeholder="https://docs.google.com/..."
              className="w-full h-10 pl-9 pr-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={submitting}
          >
            Hủy
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={submitting}
          >
            Tạo Deadline
          </Button>
        </div>
      </form>
    </Modal>
  );
};
