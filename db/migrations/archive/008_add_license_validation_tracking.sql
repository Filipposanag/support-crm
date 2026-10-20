-- Add license validation tracking fields
-- This allows tracking of online validation attempts and offline grace period

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS last_online_validation DATETIME NULL COMMENT 'Last successful online license validation';

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS last_validation_attempt DATETIME NULL COMMENT 'Last license validation attempt (success or fail)';

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS offline_since DATETIME NULL COMMENT 'When the app went offline (first failed validation)';
