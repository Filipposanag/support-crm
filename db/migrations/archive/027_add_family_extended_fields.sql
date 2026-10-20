-- Migration 027: Add extended family fields
-- Adds: father_name, spouse_maiden_name, is_divorced, spouse_deceased, is_association_member
-- Adds to members: mother_name, is_deceased, is_disabled

-- Add new columns to families table
ALTER TABLE families 
    ADD COLUMN IF NOT EXISTS father_name VARCHAR(100) COMMENT 'Father name (Όνομα Πατρός)' AFTER first_name,
    ADD COLUMN IF NOT EXISTS spouse_maiden_name VARCHAR(100) COMMENT 'Spouse maiden name (Γένος Συζύγου)' AFTER spouse_name,
    ADD COLUMN IF NOT EXISTS is_divorced TINYINT(1) DEFAULT 0 COMMENT 'Divorced status (1=yes, 0=no)',
    ADD COLUMN IF NOT EXISTS spouse_deceased TINYINT(1) DEFAULT 0 COMMENT 'Widowed/Χήρος-α (1=yes, 0=no)',
    ADD COLUMN IF NOT EXISTS is_association_member TINYINT(1) DEFAULT 0 COMMENT 'Association member - allows free subscription';

-- Add new columns to members table
ALTER TABLE members
    ADD COLUMN IF NOT EXISTS mother_name VARCHAR(100) COMMENT 'Mother name (Όνομα Μητρός)' AFTER last_name,
    ADD COLUMN IF NOT EXISTS is_deceased TINYINT(1) DEFAULT 0 COMMENT 'Deceased status (1=yes, 0=no)',
    ADD COLUMN IF NOT EXISTS is_disabled TINYINT(1) DEFAULT 0 COMMENT 'Disabled/AMEA status (1=yes, 0=no)';

-- Add index for spouse_maiden_name search
CREATE INDEX IF NOT EXISTS idx_families_spouse_maiden_name ON families(spouse_maiden_name);
