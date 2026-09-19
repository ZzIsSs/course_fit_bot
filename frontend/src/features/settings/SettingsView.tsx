import React from 'react';
import { Radio, RefreshCw, CheckCircle2, ShieldCheck, Database, Calendar as CalIcon, MessageSquare } from 'lucide-react';
import { Button } from '../../components/ui/Button';

interface SettingsViewProps {
  onManualRefresh: () => Promise<void>;
  refreshing: boolean;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onManualRefresh, refreshing }) => {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Cài đặt Hệ thống & Tích hợp Đồng bộ
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Kiểm tra tình trạng vận hành các dịch vụ Serverless, kết nối cơ sở dữ liệu và quản lý tích hợp.
        </p>
      </div>

      {/* System Health Card */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 flex items-center justify-center text-emerald-600">
            <Radio className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Tất cả dịch vụ đang hoạt động (100% Online)
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300">
                Healthy
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Chu kỳ quét Cron tự động: Mỗi 30 phút trên GitHub Actions.
            </p>
          </div>
        </div>

        <Button
          onClick={onManualRefresh}
          loading={refreshing}
          variant="outline"
          icon={<RefreshCw className="w-4 h-4" />}
          className="shrink-0"
        >
          Làm mới dữ liệu
        </Button>
      </div>

      {/* 3rd Party Integrations Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* 1. Discord Bot */}
        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  Discord Bot & Server
                </h4>
                <p className="text-[11px] text-slate-400">ID: 1499005355055648768</p>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            Tự động tạo kênh chuẩn mã môn (`#nmttnt-csc10014`), tạo Scheduled Event và mở Thread thảo luận bài tập.
          </p>
        </div>

        {/* 2. Google Calendar */}
        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600">
                <CalIcon className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  Google Calendar Sync
                </h4>
                <p className="text-[11px] text-slate-400">Service Account Key</p>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            Đồng bộ bài tập lên Google Calendar kèm chuông thông báo 24h & 3h. Đổi sang màu Xanh lá khi nộp bài.
          </p>
        </div>

        {/* 3. Supabase PostgreSQL */}
        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  Supabase PostgreSQL
                </h4>
                <p className="text-[11px] text-slate-400">aws-0-ap-northeast-1 (Tokyo)</p>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            Lưu trữ trạng thái 7 bảng quan hệ: Môn học, Deadlines, Thông báo, Modules, Phản hồi và Nhật ký lỗi.
          </p>
        </div>

        {/* 4. Notion Workspace */}
        <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                  Notion Todo Database
                </h4>
                <p className="text-[11px] text-slate-400">Internal API Token</p>
              </div>
            </div>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>

          <p className="text-xs text-slate-600 dark:text-slate-400">
            Tự động tạo thẻ công việc Todo List trên bảng Notion và đồng bộ trạng thái tick hoàn thành hai chiều.
          </p>
        </div>
      </div>
    </div>
  );
};
