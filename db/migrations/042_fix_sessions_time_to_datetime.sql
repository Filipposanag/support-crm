-- Migration 042: Fix support_sessions time columns to datetime
-- Date: 2026-01-26
-- Description: Change start_time and end_time from TIME to DATETIME for proper session tracking

-- Modify start_time to DATETIME
ALTER TABLE support_sessions
MODIFY COLUMN start_time DATETIME COMMENT 'Session start datetime';

-- Modify end_time to DATETIME  
ALTER TABLE support_sessions
MODIFY COLUMN end_time DATETIME COMMENT 'Session end datetime';

-- Update any existing records that have TIME values
-- (This will set them to today's date + the time, which is better than losing the data)
UPDATE support_sessions
SET start_time = CONCAT(CURDATE(), ' ', start_time)
WHERE start_time IS NOT NULL AND DATE(start_time) = '0000-00-00';

UPDATE support_sessions
SET end_time = CONCAT(CURDATE(), ' ', end_time)
WHERE end_time IS NOT NULL AND DATE(end_time) = '0000-00-00';
