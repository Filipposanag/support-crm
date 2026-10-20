-- Migration 037: Support CRM Transformation
-- Date: 2026-01-24
-- Description: Add all Support CRM fields to existing databases

-- Add Support CRM fields to families table
ALTER TABLE families 
ADD COLUMN IF NOT EXISTS company_name VARCHAR(200) DEFAULT '' COMMENT 'Company/Business name for corporate clients'
AFTER first_name;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS notes_support TEXT COMMENT 'Support-specific notes (technical issues, solutions, etc.)'
AFTER notes;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS rustdesk_id VARCHAR(50) DEFAULT '' COMMENT 'RustDesk ID for remote support'
AFTER notes_support;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS rustdesk_password VARCHAR(100) DEFAULT '' COMMENT 'RustDesk password (optional)'
AFTER rustdesk_id;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS support_plan ENUM('hourly', 'monthly', 'yearly', 'custom') DEFAULT 'hourly' COMMENT 'Support billing plan type'
AFTER rustdesk_password;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS hourly_rate DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Hourly support rate in EUR'
AFTER support_plan;

ALTER TABLE families 
ADD COLUMN IF NOT EXISTS monthly_rate DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monthly support rate in EUR'
AFTER hourly_rate;

-- Add indexes
ALTER TABLE families 
ADD INDEX IF NOT EXISTS idx_families_company_name (company_name);

ALTER TABLE families 
ADD INDEX IF NOT EXISTS idx_families_rustdesk_id (rustdesk_id);

-- Add RustDesk settings to app_settings
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS rustdesk_server_host VARCHAR(255) DEFAULT '' COMMENT 'RustDesk server hostname'
AFTER auto_check_updates;

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS rustdesk_server_port INT DEFAULT 21116 COMMENT 'RustDesk server port'
AFTER rustdesk_server_host;

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS rustdesk_api_key VARCHAR(255) DEFAULT '' COMMENT 'RustDesk API key'
AFTER rustdesk_server_port;

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS rustdesk_relay_server VARCHAR(255) DEFAULT '' COMMENT 'RustDesk relay server'
AFTER rustdesk_api_key;

ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS default_hourly_rate DECIMAL(10,2) DEFAULT 50.00 COMMENT 'Default hourly support rate in EUR'
AFTER rustdesk_relay_server;

-- Create sessions table for support session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    client_id       INT NOT NULL COMMENT 'Reference to families (clients) table',
    session_type    ENUM('remote', 'onsite', 'phone', 'email') DEFAULT 'remote' COMMENT 'Type of support session',
    session_date    DATE NOT NULL COMMENT 'Session date',
    start_time      TIME COMMENT 'Session start time',
    end_time        TIME COMMENT 'Session end time',
    duration_minutes INT DEFAULT 0 COMMENT 'Session duration in minutes',
    description     TEXT COMMENT 'Session description/notes',
    issue_summary   VARCHAR(255) COMMENT 'Brief issue summary',
    resolution      TEXT COMMENT 'Resolution/solution provided',
    hourly_rate     DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Hourly rate for this session',
    total_cost      DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Total cost (calculated)',
    is_billable     TINYINT(1) DEFAULT 1 COMMENT 'Is this session billable',
    is_billed       TINYINT(1) DEFAULT 0 COMMENT 'Has this session been billed',
    payment_id      INT NULL COMMENT 'Reference to payment if billed',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Foreign key constraints
    FOREIGN KEY (client_id) REFERENCES families(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    
    -- Indexes for performance
    INDEX idx_sessions_client (client_id),
    INDEX idx_sessions_date (session_date),
    INDEX idx_sessions_type (session_type),
    INDEX idx_sessions_billable (is_billable, is_billed),
    INDEX idx_sessions_payment (payment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support session records for billing and tracking';
