-- Migration: Add AFM (Tax ID) field to app_settings
-- Date: 2025-11-24
-- Description: Adds org_afm column to store the organization's tax identification number

-- Add org_afm column to app_settings table (only if it doesn't exist)
ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS org_afm VARCHAR(20) DEFAULT '' COMMENT 'Organization Tax ID (AFM)';
