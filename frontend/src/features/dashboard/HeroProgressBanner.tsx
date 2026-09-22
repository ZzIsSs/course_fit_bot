import React from 'react';
import { Award, Sparkles, ArrowRight } from 'lucide-react';
import { ProgressBar } from '../../components/ui/ProgressBar';
import { getCurrentSemester } from '../../utils/dateUtils';

interface HeroBannerProps {
  completionRate: number;
  completedCount: number;
  totalCount: number;
  semesterLabel?: string;
  onViewAllDeadlines: () => void;
}

export const HeroProgressBanner: React.FC<HeroBannerProps> = ({
  completionRate = 0,
  completedCount = 0,
  totalCount = 0,
  semesterLabel,
  onViewAllDeadlines,
}) => {
  const safeRate = isNaN(completionRate) ? 0 : Math.max(0, Math.min(100, completionRate));
  const currentSemesterLabel = semesterLabel || getCurrentSemester().label;

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-900 via-brand-700 to-blue-600 text-white p-6 sm:p-8 shadow-xl shadow-brand-900/10">
      {/* Background ambient blur decorations */}
      <div className="absolute -top-16 -right-16 w-64 h-64 bg-blue-400/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-16 -left-16 w-64 h-64 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="max-w-xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md text-xs font-semibold tracking-wide text-blue-100 mb-3 border border-white/15">
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            Bảng điều khiển {currentSemesterLabel}
          </div>

          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
            Chào mừng bạn đến với Course FIT!
          </h2>

          <p className="text-sm text-blue-100 leading-relaxed">
            {safeRate >= 80
              ? 'Thành tích xuất sắc! Bạn đã gần như giải quyết toàn bộ bài tập lớn và bài tập tuần.'
              : safeRate >= 50
              ? 'Tiến độ rất ổn định! Hãy tiếp tục duy trì để không dồn việc vào tuần thi.'
              : 'Hãy chú ý các bài tập sắp tới hạn dưới 24 giờ để đảm bảo không bị trừ điểm chuyên cần.'}
          </p>
        </div>

        {/* Quick action button */}
        <button
          onClick={onViewAllDeadlines}
          className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white text-brand-900 font-semibold text-sm shadow-md hover:bg-blue-50 transition-all active:scale-[0.98]"
        >
          <span>Xem tất cả bài tập</span>
          <ArrowRight className="w-4 h-4 text-brand-600" />
        </button>
      </div>

      {/* Progress Bar Container */}
      <div className="relative z-10 mt-6 pt-6 border-t border-white/15">
        <div className="flex items-center justify-between text-xs font-semibold mb-2">
          <span className="flex items-center gap-1.5 text-blue-100">
            <Award className="w-4 h-4 text-amber-300" />
            Tiến độ hoàn thành học kỳ
          </span>
          <span className="text-white font-bold text-sm">
            {completedCount} / {totalCount} bài tập ({safeRate.toFixed(1)}%)
          </span>
        </div>

        <ProgressBar value={safeRate} height={10} color="emerald" />
      </div>
    </div>
  );
};
