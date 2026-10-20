-- Migration 030: Add subscriptions column preferences
-- Description: Add columns for storing subscriptions view column preferences

-- Add subscriptions_visible_columns column
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS subscriptions_visible_columns TEXT DEFAULT NULL
COMMENT 'JSON array of visible column keys for subscriptions view';

-- Add subscriptions_columns_locked column
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS subscriptions_columns_locked TINYINT(1) DEFAULT 0
COMMENT 'Lock column widths for subscriptions view';
