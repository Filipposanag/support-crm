-- Migration 026: Add family_counter to app_settings
-- Stores the next family number (legacy_code) for auto-numbering

ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS family_counter INT DEFAULT 1;

-- Set initial value based on max existing legacy_code
UPDATE app_settings 
SET family_counter = COALESCE(
    (SELECT MAX(CAST(legacy_code AS UNSIGNED)) + 1 FROM families WHERE legacy_code REGEXP '^[0-9]+$'),
    1
)
WHERE family_counter = 1 OR family_counter IS NULL;
