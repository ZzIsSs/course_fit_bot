import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import { ToastMessage } from '../../types';

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  return (
    <div
      aria-live="assertive"
      className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm w-full pointer-events-none p-2 sm:p-0"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

interface ToastItemProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onDismiss }) => {
  // Defensive: Tự hủy sau 4s kèm cleanup tránh memory leak
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, 4000);

    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />,
    info: <Info className="w-5 h-5 text-blue-500 shrink-0" />,
  }[toast.type];

  const borderStyles = {
    success: 'border-emerald-200 dark:border-emerald-800/50 bg-emerald-50/90 dark:bg-slate-900/90',
    error: 'border-rose-200 dark:border-rose-800/50 bg-rose-50/90 dark:bg-slate-900/90',
    warning: 'border-amber-200 dark:border-amber-800/50 bg-amber-50/90 dark:bg-slate-900/90',
    info: 'border-blue-200 dark:border-blue-800/50 bg-blue-50/90 dark:bg-slate-900/90',
  }[toast.type];

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-lg backdrop-blur-md transition-all duration-300 animate-in slide-in-from-bottom-5 ${borderStyles}`}
    >
      {icons}
      <div className="flex-1 min-w-0">
        {toast.title && (
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white truncate">
            {toast.title}
          </h4>
        )}
        <p className="text-xs text-slate-700 dark:text-slate-300 break-words mt-0.5">
          {toast.message}
        </p>
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        aria-label="Đóng thông báo"
        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
