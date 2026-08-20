-- ==================== KHÓA HỌC ====================

create table courses(
    courses_id serial primary key,
    course_name varchar(255) not null unique,
    display_name varchar(255),               -- Tên tiếng Việt hiển thị
    lms_courses_id varchar(50) not null unique,
    chat_id varchar(50) unique,              -- Discord channel ID, NULL khi chưa tạo channel
    last_crawled_time timestamp
);

-- ==================== DEADLINE ====================

create table deadlines(
    deadlines_id serial primary key,
    courses_id int not null,
    constraint fk_deadlines_courses foreign key (courses_id) references courses(courses_id),
    deadline_name varchar(255) not null,
    lms_deadlines_id varchar(50) not null unique,
    due_time timestamp not null,
    created_time timestamp not null default now(),
    source_url varchar(500) not null,

    -- Trạng thái theo dõi thông báo (thay thế state.json)
    notified_new boolean not null default false,
    reminded_3d boolean not null default false,
    reminded_1d boolean not null default false,
    completed boolean not null default false,
    completed_by varchar(100),
    discord_message_id varchar(50),
    discord_channel_id varchar(50),
    discord_event_id varchar(50)
);

-- ==================== THÔNG BÁO MÔN HỌC ====================

create table announcements(
    announcements_id serial primary key,
    courses_id int not null,
    constraint fk_announcements_courses foreign key (courses_id) references courses(courses_id),
    announcements_name varchar(255) not null,
    lms_announcements_id varchar(50) not null unique,
    created_time timestamp not null default now(),
    source_url varchar(500) not null
);

-- ==================== NỘI DUNG KHÓA HỌC (Modules) ====================
-- Theo dõi tài liệu, bài tập, quiz, ... được upload trên Moodle.
-- Tương ứng với state['moodle']['known_modules'] trong code cũ.

create table course_modules(
    module_id serial primary key,
    courses_id int not null,
    constraint fk_modules_courses foreign key (courses_id) references courses(courses_id),
    lms_module_id varchar(50) not null,
    module_type varchar(30) not null,        -- 'resource', 'assign', 'quiz', 'url', ...
    module_name varchar(255) not null,
    time_modified timestamp,
    unique(courses_id, lms_module_id)
);

-- ==================== BÀI ĐĂNG DIỄN ĐÀN ====================
-- Theo dõi bài đăng mới của giảng viên trên diễn đàn Moodle.
-- Tương ứng với state['moodle']['known_discussions'] trong code cũ.

create table forum_discussions(
    discussion_id serial primary key,
    courses_id int not null,
    constraint fk_discussions_courses foreign key (courses_id) references courses(courses_id),
    lms_discussion_id varchar(50) not null unique,
    forum_name varchar(255),
    subject varchar(255),
    author varchar(100),
    created_time timestamp not null default now()
);

-- ==================== THÔNG BÁO ĐÃ GỬI (Notifications) ====================
-- reference_id trỏ đến deadlines_id hoặc announcements_id tùy theo giá trị của cột 'type'.
-- Không thể dùng Foreign Key vì reference đa hình (polymorphic).

create table notifications(
    notifications_id serial primary key,
    type varchar(50) not null check(type in ('deadline', 'announcement')),
    sent_at timestamp,
    message text not null,
    created_at timestamp not null default now(),
    reference_id int not null
);

create index idx_notifications_ref on notifications (type, reference_id);

-- ==================== NHẬT KÝ LỖI (Error Logs) ====================

create table error_logs(
    error_logs_id serial primary key,
    source varchar(50) not null check (source in ('moodle_calendar', 'moodle_api', 'discord_api', 'system', 'other')),
    severity varchar(20) not null default 'error' check (severity in ('warning', 'error', 'critical')),
    command varchar(50),
    reference_type varchar(50) check (reference_type in ('course', 'deadline', 'announcement', 'notification', 'module', 'discussion', 'other')),
    reference_id int,
    error_message varchar(500) not null,
    error_detail text,
    context jsonb,
    occurred_at timestamp not null default now()
);

create index idx_error_logs_source_time on error_logs (source, occurred_at desc);
create index idx_error_logs_reference on error_logs (reference_type, reference_id);
create index idx_error_logs_critical on error_logs (occurred_at) where severity = 'critical';
