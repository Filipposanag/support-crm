-- Migration 043: Add duration_seconds to support_sessions
-- Date: 2026-01-26
-- Description: Add duration_seconds column for precise duration tracking

-- Add duration_seconds column
ALTER TABLE support_sessions
ADD COLUMN duration_seconds INT DEFAULT 0 COMMENT 'Session duration in seconds (for precise tracking)';

-- Update existing records to calculate seconds from minutes
UPDATE support_sessions
SET duration_seconds = duration_minutes * 60
WHERE duration_seconds = 0 AND duration_minutes > 0;
