-- Migration 009: Add family_number field to families table
-- Adds a family number field for tracking family numbers

-- Add family_number field
ALTER TABLE families
ADD COLUMN IF NOT EXISTS family_number VARCHAR(50) COMMENT 'Auto-generated family number';

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_families_family_number ON families(family_number);
