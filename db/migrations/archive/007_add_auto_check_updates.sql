-- Migration: Add auto_check_updates field to app_settings
-- Date: 2025-11-23
-- Description: Adds auto_check_updates boolean field for automatic update checking on startup

-- Add auto_check_updates column if it doesn't exist
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS auto_check_updates BOOLEAN DEFAULT TRUE
COMMENT 'Enable automatic update checking on application startup';

-- Set default value for existing row
UPDATE app_settings 
SET auto_check_updates = TRUE 
WHERE id = 1 AND auto_check_updates IS NULL;
