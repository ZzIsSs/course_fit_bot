export type DeadlineSource = 'moodle' | 'manual' | 'external';

export interface Course {
  courses_id: number;
  course_name: string;
  display_name?: string | null;
  lms_courses_id: string;
  chat_id?: string | null;
  discord_category_id?: string | null;
  pending_deadlines_count?: number;
}

export interface Deadline {
  deadlines_id: number;
  courses_id: number;
  course_name: string;
  course_display_name?: string | null;
  deadline_name: string;
  due_time: string;
  due_time_vn?: string;
  source_url?: string;
  source: DeadlineSource;
  added_by?: string | null;
  completed: boolean;
  completed_by?: string | null;
  is_urgent?: boolean;
  is_overdue?: boolean;
  countdown_text?: string;
  discord_channel_id?: string | null;
  discord_message_id?: string | null;
}

export interface SemesterInfo {
  semester: 1 | 2 | 3;
  academicYear: string;
  label: string;
}

export interface DashboardStats {
  total_deadlines: number;
  completed_deadlines: number;
  pending_deadlines: number;
  completion_rate: number;
  urgent_24h: number;
  upcoming_3d: number;
  overdue: number;
  total_courses: number;
  semester?: SemesterInfo;
}

export interface Announcement {
  announcements_id: number;
  courses_id: number;
  course_name: string;
  announcements_name: string;
  source_url: string;
  created_time: string;
  author?: string;
  ai_summary?: string[];
}

export interface CourseModule {
  module_id: number;
  courses_id: number;
  course_name: string;
  module_type: 'resource' | 'assign' | 'quiz' | 'url' | 'folder' | string;
  module_name: string;
  time_modified?: string | null;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title?: string;
  message: string;
}

export type ActiveTab = 'overview' | 'deadlines' | 'courses' | 'announcements' | 'settings';
export type ViewMode = 'list' | 'kanban';
export type FilterStatus = 'all' | 'pending' | 'urgent' | 'completed' | 'overdue';
