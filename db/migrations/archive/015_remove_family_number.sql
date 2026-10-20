-- Migration 015: Remove family_number field and use legacy_code for auto-numbering
-- Date: November 21, 2025
-- Description: Simplifies family numbering by using only legacy_code field

-- Step 1: Ensure all families have a legacy_code
-- Generate legacy_code for any families that don't have one
UPDATE families
SET legacy_code = (
    SELECT COALESCE(MAX(f2.legacy_code), 0) + 1
    FROM families f2
    WHERE f2.legacy_code IS NOT NULL
)
WHERE legacy_code IS NULL OR legacy_code = 0;

-- Step 2: Make legacy_code NOT NULL (it's now required)
ALTER TABLE families
MODIFY COLUMN legacy_code INT NOT NULL COMMENT 'Family code (used for auto-numbering)';

-- Step 3: Drop the family_number column and its index
DROP INDEX IF EXISTS idx_families_family_number ON families;
ALTER TABLE families
DROP COLUMN IF EXISTS family_number;

-- Step 4: Remove family numbering settings from app_settings
ALTER TABLE app_settings
DROP COLUMN IF EXISTS family_counter,
DROP COLUMN IF EXISTS family_prefix;

-- Record migration
INSERT INTO schema_migrations (version, description)
VALUES (15, 'Remove family_number field and use legacy_code for auto-numbering')
ON DUPLICATE KEY UPDATE description = description;
