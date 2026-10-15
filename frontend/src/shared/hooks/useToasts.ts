import { useCallback, useState } from 'react';
import { ToastMessage } from '@/shared/types';

export type ToastType = 'success' | 'error' | 'info' | 'warning';
export type AddToast = (type: ToastType, message: string, title?: string) => void;

/** Danh sách toast đang hiển thị, kèm hàm thêm / tắt toast. */
export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback<AddToast>((type, message, title) => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, type, message, title }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, addToast, dismissToast };
}
