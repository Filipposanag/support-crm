-- Migration: Add is_free to subscriptions visible columns
-- Date: 2025-12-06
-- Description: Updates existing subscriptions_visible_columns to include is_free field

-- Update existing settings to include is_free in subscriptions_visible_columns
-- Only update if the column exists and doesn't already contain is_free
UPDATE app_settings 
SET subscriptions_visible_columns = REPLACE(
    subscriptions_visible_columns, 
    '"status"', 
    '"is_free", "status"'
)
WHERE id = 1 
  AND subscriptions_visible_columns IS NOT NULL 
  AND subscriptions_visible_columns NOT LIKE '%is_free%';
