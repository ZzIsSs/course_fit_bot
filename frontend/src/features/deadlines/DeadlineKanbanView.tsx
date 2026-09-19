import React from 'react';
import { Deadline } from '../../types';
import { DeadlineItemCard } from './DeadlineItemCard';
import { getCountdown } from '../../utils/dateUtils';
import { CheckCircle2, Flame, ListTodo } from 'lucide-react';

interface DeadlineKanbanViewProps {
  deadlines: Deadline[];
  onToggleComplete: (id: number, currentCompleted: boolean) => void;
}

export const DeadlineKanbanView: React.FC<DeadlineKanbanViewProps> = ({
  deadlines = [],
  onToggleComplete,
}) => {
  const todoList: Deadline[] = [];
  const urgentList: Deadline[] = [];
  const doneList: Deadline[] = [];

  deadlines.forEach((d) => {
    if (d.completed) {
      doneList.push(d);
      return;
    }
    const c = getCountdown(d.due_time);
    if (c.isUrgent || c.diffHours < 48) {
      urgentList.push(d);
    } else {
      todoList.push(d);
    }
  });

  const columns = [
    {
      title: 'Cần làm (To-Do)',
      count: todoList.length,
      icon: <ListTodo className="w-4 h-4 text-slate-500" />,
      items: todoList,
      borderColor: 'border-slate-200 dark:border-slate-800',
    },
    {
      title: 'Khẩn cấp / Gấp',
      count: urgentList.length,
      icon: <Flame className="w-4 h-4 text-red-500 animate-pulse" />,
      items: urgentList,
      borderColor: 'border-red-200 dark:border-red-900/40 bg-red-50/10 dark:bg-red-950/10',
    },
    {
      title: 'Đã hoàn thành (Done)',
      count: doneList.length,
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
      items: doneList,
      borderColor: 'border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/10 dark:bg-emerald-950/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-start">
      {columns.map((col, index) => (
        <div
          key={index}
          className={`flex flex-col rounded-2xl border p-4 bg-slate-50/60 dark:bg-slate-900/40 ${col.borderColor}`}
        >
          {/* Column Header */}
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              {col.icon}
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                {col.title}
              </h3>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              {col.count}
            </span>
          </div>

          {/* Cards List */}
          <div className="space-y-3 min-h-[160px]">
            {col.items.length === 0 ? (
              <div className="h-24 flex items-center justify-center text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                Không có bài tập
              </div>
            ) : (
              col.items.map((item) => (
                <DeadlineItemCard
                  key={item.deadlines_id}
                  deadline={item}
                  onToggleComplete={onToggleComplete}
                  compact={true}
                />
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
