-- Migration 035: Add security settings table
-- Date: 2025-12-07
-- Description: Creates table for storing security configuration

-- Create security_settings table
CREATE TABLE IF NOT EXISTS security_settings (
    id INT PRIMARY KEY DEFAULT 1,
    -- Brute-force protection
    brute_force_enabled BOOLEAN DEFAULT TRUE COMMENT 'Enable brute-force protection',
    max_failed_attempts INT DEFAULT 5 COMMENT 'Max failed login attempts before lockout',
    lockout_duration_minutes INT DEFAULT 15 COMMENT 'Account lockout duration in minutes',
    -- Password policy
    password_min_length INT DEFAULT 6 COMMENT 'Minimum password length',
    password_require_uppercase BOOLEAN DEFAULT FALSE COMMENT 'Require uppercase letter',
    password_require_lowercase BOOLEAN DEFAULT FALSE COMMENT 'Require lowercase letter',
    password_require_number BOOLEAN DEFAULT FALSE COMMENT 'Require number',
    password_require_special BOOLEAN DEFAULT FALSE COMMENT 'Require special character',
    -- Session settings
    session_duration_hours INT DEFAULT 8 COMMENT 'Session duration in hours',
    -- Encryption (bcrypt rounds)
    bcrypt_rounds INT DEFAULT 12 COMMENT 'Bcrypt hashing rounds (10-14 recommended)',
    -- Timestamps
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by INT NULL COMMENT 'User who last updated settings',
    CONSTRAINT chk_max_attempts CHECK (max_failed_attempts >= 1 AND max_failed_attempts <= 20),
    CONSTRAINT chk_lockout_duration CHECK (lockout_duration_minutes >= 1 AND lockout_duration_minutes <= 1440),
    CONSTRAINT chk_password_length CHECK (password_min_length >= 4 AND password_min_length <= 32),
    CONSTRAINT chk_session_duration CHECK (session_duration_hours >= 1 AND session_duration_hours <= 168),
    CONSTRAINT chk_bcrypt_rounds CHECK (bcrypt_rounds >= 8 AND bcrypt_rounds <= 16)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Security configuration settings';

-- Insert default settings
INSERT IGNORE INTO security_settings (id) VALUES (1);

-- Record migration
INSERT INTO schema_migrations (version, description) VALUES (35, 'Add Security Settings');
