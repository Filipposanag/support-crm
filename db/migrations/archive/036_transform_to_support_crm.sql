-- Migration 036: Transform to Support CRM
-- Rename families to clients, add RustDesk fields, create support_sessions table
-- Date: 2025-01-24

-- ============================================================================
-- Step 1: Rename families table to clients
-- ============================================================================

-- Rename the table
ALTER TABLE families RENAME TO clients;

-- Update audit log references
UPDATE audit_log SET table_name = 'clients' WHERE table_name = 'families';

-- ============================================================================
-- Step 2: Add RustDesk and Support fields to clients
-- ============================================================================

ALTER TABLE clients
ADD COLUMN rustdesk_id VARCHAR(100) DEFAULT '' COMMENT 'RustDesk client ID for remote connection',
ADD COLUMN rustdesk_password VARCHAR(255) DEFAULT '' COMMENT 'RustDesk password (encrypted)',
ADD COLUMN support_plan VARCHAR(50) DEFAULT 'hourly' COMMENT 'Support plan type: hourly, monthly, yearly, custom',
ADD COLUMN hourly_rate DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Hourly support rate (for hourly plan)',
ADD COLUMN monthly_rate DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monthly subscription rate',
ADD COLUMN notes_support TEXT COMMENT 'Support-specific notes and history',
ADD INDEX idx_clients_rustdesk_id (rustdesk_id);

-- ============================================================================
-- Step 3: Create support_sessions table
-- ============================================================================

CREATE TABLE IF NOT EXISTS support_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL COMMENT 'Reference to clients table',
    session_type VARCHAR(50) DEFAULT 'remote' COMMENT 'Session type: remote, onsite, phone, email',
    start_time DATETIME NOT NULL COMMENT 'Session start timestamp',
    end_time DATETIME COMMENT 'Session end timestamp (NULL if ongoing)',
    duration_minutes INT DEFAULT 0 COMMENT 'Session duration in minutes (calculated)',
    rustdesk_session_id VARCHAR(100) COMMENT 'RustDesk session identifier',
    technician VARCHAR(100) COMMENT 'Technician/support person name',
    description TEXT COMMENT 'Session description/notes',
    issue_summary TEXT COMMENT 'Summary of issue resolved',
    status VARCHAR(20) DEFAULT 'active' COMMENT 'Session status: active, completed, cancelled',
    billed_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Amount billed for this session',
    payment_id INT COMMENT 'Reference to payment record (if billed)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Foreign key constraints
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    
    -- Indexes for performance
    INDEX idx_sessions_client (client_id),
    INDEX idx_sessions_start_time (start_time),
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_technician (technician),
    INDEX idx_sessions_payment (payment_id),
    INDEX idx_sessions_type (session_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support session tracking and billing';

-- ============================================================================
-- Step 4: Update foreign key references (family_id → client_id)
-- ============================================================================

-- Note: We keep the column names as family_id for backward compatibility
-- with existing code. We'll update the code to use client_id terminology.
-- The actual column rename will be done in a separate migration if needed.

-- ============================================================================
-- Step 5: Update app_settings for Support CRM
-- ============================================================================

-- Add RustDesk configuration fields
ALTER TABLE app_settings
ADD COLUMN rustdesk_server_host VARCHAR(255) DEFAULT '' COMMENT 'RustDesk server hostname/IP',
ADD COLUMN rustdesk_server_port INT DEFAULT 21116 COMMENT 'RustDesk server port',
ADD COLUMN rustdesk_api_key VARCHAR(255) DEFAULT '' COMMENT 'RustDesk API key (if applicable)',
ADD COLUMN rustdesk_relay_server VARCHAR(255) DEFAULT '' COMMENT 'RustDesk relay server address',
ADD COLUMN default_hourly_rate DECIMAL(10,2) DEFAULT 50.00 COMMENT 'Default hourly support rate',
ADD COLUMN default_monthly_rate DECIMAL(10,2) DEFAULT 200.00 COMMENT 'Default monthly subscription rate',
ADD COLUMN session_rounding_minutes INT DEFAULT 15 COMMENT 'Round session duration to nearest X minutes';

-- Update organization name
UPDATE app_settings 
SET org_name = 'Support CRM',
    org_short_name = 'Support CRM'
WHERE id = 1;

-- ============================================================================
-- Step 6: Create audit triggers for support_sessions
-- ============================================================================

DELIMITER $$

-- Trigger for INSERT operations on support_sessions
DROP TRIGGER IF EXISTS trg_support_sessions_after_insert$$
CREATE TRIGGER trg_support_sessions_after_insert
AFTER INSERT ON support_sessions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'support_sessions',
        NEW.id,
        'INSERT',
        NULL,
        JSON_OBJECT(
            'client_id', NEW.client_id,
            'session_type', NEW.session_type,
            'start_time', NEW.start_time,
            'end_time', NEW.end_time,
            'duration_minutes', NEW.duration_minutes,
            'technician', NEW.technician,
            'status', NEW.status,
            'billed_amount', NEW.billed_amount
        ),
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

-- Trigger for UPDATE operations on support_sessions
DROP TRIGGER IF EXISTS trg_support_sessions_after_update$$
CREATE TRIGGER trg_support_sessions_after_update
AFTER UPDATE ON support_sessions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'support_sessions',
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'client_id', OLD.client_id,
            'session_type', OLD.session_type,
            'start_time', OLD.start_time,
            'end_time', OLD.end_time,
            'duration_minutes', OLD.duration_minutes,
            'technician', OLD.technician,
            'status', OLD.status,
            'billed_amount', OLD.billed_amount
        ),
        JSON_OBJECT(
            'client_id', NEW.client_id,
            'session_type', NEW.session_type,
            'start_time', NEW.start_time,
            'end_time', NEW.end_time,
            'duration_minutes', NEW.duration_minutes,
            'technician', NEW.technician,
            'status', NEW.status,
            'billed_amount', NEW.billed_amount
        ),
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

-- Trigger for DELETE operations on support_sessions
DROP TRIGGER IF EXISTS trg_support_sessions_after_delete$$
CREATE TRIGGER trg_support_sessions_after_delete
AFTER DELETE ON support_sessions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'support_sessions',
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'client_id', OLD.client_id,
            'session_type', OLD.session_type,
            'start_time', OLD.start_time,
            'end_time', OLD.end_time,
            'duration_minutes', OLD.duration_minutes,
            'technician', OLD.technician,
            'status', OLD.status,
            'billed_amount', OLD.billed_amount
        ),
        NULL,
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

DELIMITER ;

-- ============================================================================
-- Step 7: Update audit triggers for clients (renamed from families)
-- ============================================================================

DELIMITER $$

-- Drop old families triggers
DROP TRIGGER IF EXISTS trg_families_after_insert$$
DROP TRIGGER IF EXISTS trg_families_after_update$$
DROP TRIGGER IF EXISTS trg_families_after_delete$$

-- Create new clients triggers
DROP TRIGGER IF EXISTS trg_clients_after_insert$$
CREATE TRIGGER trg_clients_after_insert
AFTER INSERT ON clients
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'clients',
        NEW.id,
        'INSERT',
        NULL,
        JSON_OBJECT(
            'legacy_code', NEW.legacy_code,
            'last_name', NEW.last_name,
            'first_name', NEW.first_name,
            'rustdesk_id', NEW.rustdesk_id,
            'support_plan', NEW.support_plan,
            'hourly_rate', NEW.hourly_rate,
            'is_active', NEW.is_active
        ),
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

DROP TRIGGER IF EXISTS trg_clients_after_update$$
CREATE TRIGGER trg_clients_after_update
AFTER UPDATE ON clients
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'clients',
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'legacy_code', OLD.legacy_code,
            'last_name', OLD.last_name,
            'first_name', OLD.first_name,
            'rustdesk_id', OLD.rustdesk_id,
            'support_plan', OLD.support_plan,
            'hourly_rate', OLD.hourly_rate,
            'is_active', OLD.is_active
        ),
        JSON_OBJECT(
            'legacy_code', NEW.legacy_code,
            'last_name', NEW.last_name,
            'first_name', NEW.first_name,
            'rustdesk_id', NEW.rustdesk_id,
            'support_plan', NEW.support_plan,
            'hourly_rate', NEW.hourly_rate,
            'is_active', NEW.is_active
        ),
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

DROP TRIGGER IF EXISTS trg_clients_after_delete$$
CREATE TRIGGER trg_clients_after_delete
AFTER DELETE ON clients
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_by,
        changed_at
    ) VALUES (
        'clients',
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'legacy_code', OLD.legacy_code,
            'last_name', OLD.last_name,
            'first_name', OLD.first_name,
            'rustdesk_id', OLD.rustdesk_id,
            'support_plan', OLD.support_plan,
            'hourly_rate', OLD.hourly_rate,
            'is_active', OLD.is_active
        ),
        NULL,
        COALESCE(@current_user, USER()),
        NOW()
    );
END$$

DELIMITER ;

-- ============================================================================
-- Migration Complete
-- ============================================================================
