ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS source varchar(20) NOT NULL DEFAULT 'moodle';
ALTER TABLE deadlines ADD COLUMN IF NOT EXISTS added_by varchar(100);
