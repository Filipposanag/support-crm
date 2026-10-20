-- Migration: Add extended fields to members table
-- Date: 2025-12-07
-- Description: Adds mother_name, is_deceased, is_disabled columns to members table

-- Add mother_name column
ALTER TABLE members ADD COLUMN IF NOT EXISTS mother_name VARCHAR(100) COMMENT 'Mother name' AFTER last_name;

-- Add is_deceased column
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_deceased TINYINT(1) DEFAULT 0 COMMENT 'Deceased status';

-- Add is_disabled column  
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_disabled TINYINT(1) DEFAULT 0 COMMENT 'Disabled/AMEA status';
