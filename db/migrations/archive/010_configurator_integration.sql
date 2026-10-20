-- ============================================================================
-- Migration 010: Configurator Integration
-- ============================================================================
-- Ενσωματώνει τη λειτουργικότητα του configurator στο migration system
-- Δημιουργεί πίνακα για tracking της κατάστασης του configurator
-- ============================================================================

-- Δημιουργία πίνακα για tracking configurator status
CREATE TABLE IF NOT EXISTS configurator_status (
    id INT PRIMARY KEY DEFAULT 1 COMMENT 'Single row table (always id=1)',
    database_initialized TINYINT(1) DEFAULT 0 COMMENT 'Database has been initialized',
    schema_version VARCHAR(20) DEFAULT '2.0' COMMENT 'Current schema version',
    last_migration INT DEFAULT 0 COMMENT 'Last applied migration number',
    initialized_at DATETIME NULL COMMENT 'When database was first initialized',
    last_check_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last configuration check',
    
    -- Configuration tracking
    config_host VARCHAR(255) DEFAULT 'localhost' COMMENT 'Database host',
    config_port INT DEFAULT 3306 COMMENT 'Database port',
    config_database VARCHAR(100) DEFAULT 'supportcrm' COMMENT 'Database name',
    
    -- Status flags
    tables_created TINYINT(1) DEFAULT 0 COMMENT 'All tables have been created',
    default_data_inserted TINYINT(1) DEFAULT 0 COMMENT 'Default app_settings inserted',
    migrations_applied TINYINT(1) DEFAULT 0 COMMENT 'All migrations have been applied',
    
    notes TEXT COMMENT 'Additional configuration notes'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Configurator status and database initialization tracking';

-- Εισαγωγή αρχικής εγγραφής
INSERT INTO configurator_status (
    id, 
    database_initialized, 
    schema_version,
    last_migration,
    initialized_at,
    tables_created,
    default_data_inserted,
    migrations_applied
) VALUES (
    1,
    1,
    '2.0',
    10,
    NOW(),
    1,
    1,
    1
) ON DUPLICATE KEY UPDATE 
    last_migration = GREATEST(last_migration, 10),
    migrations_applied = 1,
    last_check_at = NOW();

-- Δημιουργία πίνακα για migration history
CREATE TABLE IF NOT EXISTS migration_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    migration_number INT NOT NULL COMMENT 'Migration number (e.g., 001, 002)',
    migration_name VARCHAR(255) NOT NULL COMMENT 'Migration file name',
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When migration was applied',
    success TINYINT(1) DEFAULT 1 COMMENT 'Migration applied successfully',
    error_message TEXT COMMENT 'Error message if migration failed',
    execution_time_ms INT COMMENT 'Execution time in milliseconds',
    
    UNIQUE KEY uq_migration_number (migration_number),
    INDEX idx_migration_applied (applied_at),
    INDEX idx_migration_success (success)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Migration execution history';

-- Καταγραφή όλων των προηγούμενων migrations
INSERT INTO migration_history (migration_number, migration_name, applied_at, success) VALUES
(1, '001_make_legacy_pcode_nullable.sql', NOW(), 1),
(2, '002_add_column_preferences.sql', NOW(), 1),
(3, '003_add_subscription_dates.sql', NOW(), 1),
(4, '004_add_email_notification_settings.sql', NOW(), 1),
(5, '005_add_license_management.sql', NOW(), 1),
(6, '006_add_auto_numbering.sql', NOW(), 1),
(7, '007_enforce_subscription_payment_rule.sql', NOW(), 1),
(8, '008_add_license_validation_tracking.sql', NOW(), 1),
(9, '009_migrate_existing_subscriptions.sql', NOW(), 1),
(10, '010_configurator_integration.sql', NOW(), 1)
ON DUPLICATE KEY UPDATE migration_number = migration_number;

-- Ενημέρωση app_settings με configurator metadata
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS configurator_version VARCHAR(20) DEFAULT '1.0' COMMENT 'Configurator version used',
ADD COLUMN IF NOT EXISTS last_configured_at DATETIME NULL COMMENT 'Last time configurator was run',
ADD COLUMN IF NOT EXISTS configuration_notes TEXT COMMENT 'Configuration notes from configurator';

-- ============================================================================
-- Verification Queries (για debugging)
-- ============================================================================

-- Έλεγχος κατάστασης configurator
-- SELECT * FROM configurator_status;

-- Έλεγχος migration history
-- SELECT * FROM migration_history ORDER BY migration_number;

-- Έλεγχος όλων των πινάκων
-- SHOW TABLES;

-- ============================================================================
-- Migration Complete
-- ============================================================================
