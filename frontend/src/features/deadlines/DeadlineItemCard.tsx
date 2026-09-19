import React from 'react';
import { ExternalLink, MessageSquare, Calendar, User } from 'lucide-react';
import { Deadline } from '../../types';
import { Badge } from '../../components/ui/Badge';
import { Checkbox } from '../../components/ui/Checkbox';
import { getCountdown, formatVietnameseDate } from '../../utils/dateUtils';

interface DeadlineItemCardProps {
  deadline: Deadline;
  onToggleComplete: (id: number, currentCompleted: boolean) => void;
  compact?: boolean;
}

export const DeadlineItemCard: React.FC<DeadlineItemCardProps> = ({
  deadline,
  onToggleComplete,
  compact = false,
}) => {
  const countdown = getCountdown(deadline?.due_time);
  const formattedDate = formatVietnameseDate(deadline?.due_time);

  const getStatusVariant = () => {
    if (deadline.completed) return 'completed';
    if (countdown.isOverdue) return 'overdue';
    if (countdown.isUrgent) return 'urgent';
    if (countdown.diffHours < 72) return 'soon';
    return 'normal';
  };

  return (
    <div
      className={`group flex items-start gap-3.5 p-4 rounded-xl border bg-white dark:bg-slate-900 transition-all duration-200 ${
        deadline.completed
          ? 'border-slate-200/80 dark:border-slate-800/80 opacity-75 bg-slate-50/50 dark:bg-slate-900/40'
          : countdown.isUrgent
          ? 'border-red-200 dark:border-red-900/40 shadow-xs hover:border-red-300'
          : 'border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700'
      }`}
    >
      {/* Checkbox Complete */}
      <div className="pt-0.5 shrink-0">
        <Checkbox
          checked={deadline.completed}
          onChange={() => onToggleComplete(deadline.deadlines_id, deadline.completed)}
          aria-label={`Đánh dấu ${deadline.deadline_name} là hoàn thành`}
        />
      </div>

      {/* Main Content Info */}
      <div className="flex-1 min-w-0">
        {/* Top Badges Row */}
        <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
          <Badge variant="course">
            #{deadline.course_name?.toLowerCase() ?? 'mon-hoc'}
          </Badge>

          {deadline.source === 'manual' ? (
            <Badge variant="manual" icon={false}>
              Thủ công
            </Badge>
          ) : (
            <Badge variant="moodle" icon={false}>
              Moodle
            </Badge>
          )}

          <Badge variant={getStatusVariant()}>
            {deadline.completed ? 'Đã nộp bài' : countdown.text}
          </Badge>
        </div>

        {/* Title */}
        <h4
          className={`text-sm font-semibold leading-snug break-words transition-all ${
            deadline.completed
              ? 'line-through text-slate-400 dark:text-slate-500'
              : 'text-slate-900 dark:text-slate-100 group-hover:text-brand-600 dark:group-hover:text-brand-400'
          }`}
        >
          {deadline.deadline_name || 'Không có tiêu đề bài tập'}
        </h4>

        {/* Course display name if available */}
        {deadline.course_display_name && (
          <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
            {deadline.course_display_name}
          </p>
        )}

        {/* Meta Info Row */}
        <div className="flex flex-wrap items-center gap-3 mt-2.5 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-1 shrink-0">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>Hạn: {formattedDate}</span>
          </div>

          {deadline.added_by && (
            <div className="flex items-center gap-1 shrink-0 truncate max-w-[160px]">
              <User className="w-3.5 h-3.5 text-slate-400" />
              <span className="truncate">Tạo bởi: {deadline.added_by}</span>
            </div>
          )}

          {deadline.completed && deadline.completed_by && (
            <span className="text-emerald-600 dark:text-emerald-400 font-medium truncate">
              ✓ Xong bởi: {deadline.completed_by}
            </span>
          )}
        </div>
      </div>

      {/* Action Links */}
      <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
        {deadline.source_url && (
          <a
            href={deadline.source_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Mở bài tập trên Moodle / Nguồn"
            className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        )}

        {deadline.discord_channel_id && (
          <a
            href={`discord://discord.com/channels/@me/${deadline.discord_channel_id}`}
            title="Nhảy tới kênh Discord môn học"
            className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
          </a>
        )}
      </div>
    </div>
  );
};
