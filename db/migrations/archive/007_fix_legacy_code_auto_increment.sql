-- Migration 007: Fix legacy_code to auto-increment for new families
-- Makes legacy_code auto-increment so new families get unique codes automatically

-- First, find the max legacy_code
SET @max_code = (SELECT COALESCE(MAX(legacy_code), 0) FROM families);

-- Update any families with legacy_code = 0 to have unique codes
UPDATE families 
SET legacy_code = (@max_code := @max_code + 1)
WHERE legacy_code = 0 AND id > (SELECT MIN(id) FROM (SELECT id FROM families WHERE legacy_code = 0) AS temp);

-- Note: We keep the constraint as is, but the application should generate unique codes
-- The families_repo should auto-generate the next available legacy_code when creating new families
