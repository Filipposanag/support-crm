-- Migration: Add column preferences to app_settings
-- Date: 2025-11-18
-- Description: Adds fields for storing user column visibility and lock preferences

ALTER TABLE app_settings
ADD COLUMN families_visible_columns TEXT COMMENT 'JSON array of visible column keys for families view',
ADD COLUMN families_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for families view',
ADD COLUMN payments_visible_columns TEXT COMMENT 'JSON array of visible column keys for payments view',
ADD COLUMN payments_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for payments view',
ADD COLUMN reports_visible_columns TEXT COMMENT 'JSON array of visible column keys for reports view',
ADD COLUMN reports_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for reports view';
