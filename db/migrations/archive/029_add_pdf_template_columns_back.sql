-- Migration 029: Ensure PDF template columns exist in app_settings
-- These columns are used by the PDF Template Editor to store template JSON data
-- They store the visual editor's template configuration as JSON

-- Add pdf_template_family if not exists
-- Stores JSON data for family certificate PDF template
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'app_settings' AND COLUMN_NAME = 'pdf_template_family');
SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE app_settings ADD COLUMN pdf_template_family TEXT DEFAULT NULL COMMENT ''JSON data for family certificate PDF template''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add pdf_template_payment if not exists
-- Stores JSON data for payment receipt PDF template
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'app_settings' AND COLUMN_NAME = 'pdf_template_payment');
SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE app_settings ADD COLUMN pdf_template_payment TEXT DEFAULT NULL COMMENT ''JSON data for payment receipt PDF template''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add pdf_template_subscription if not exists
-- Stores JSON data for subscription certificate PDF template
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'app_settings' AND COLUMN_NAME = 'pdf_template_subscription');
SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE app_settings ADD COLUMN pdf_template_subscription TEXT DEFAULT NULL COMMENT ''JSON data for subscription certificate PDF template''',
    'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
