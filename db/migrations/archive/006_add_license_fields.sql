-- Migration 006: Add License Management Fields
-- Adds license management fields to app_settings table

-- Add license fields to app_settings
ALTER TABLE app_settings
ADD COLUMN license_key VARCHAR(255) DEFAULT '' COMMENT 'License activation key',
ADD COLUMN license_owner VARCHAR(200) DEFAULT '' COMMENT 'License owner name',
ADD COLUMN license_start_date DATE NULL COMMENT 'License activation date',
ADD COLUMN license_end_date DATE NULL COMMENT 'License expiration date',
ADD COLUMN license_status VARCHAR(20) DEFAULT 'none' COMMENT 'License status: active, expired, none';

-- Add index for license status
CREATE INDEX idx_app_settings_license_status ON app_settings(license_status);
