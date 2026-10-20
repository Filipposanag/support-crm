-- Migration 012: Create audit_log table
-- Description: Audit log for tracking all database changes (INSERT, UPDATE, DELETE)
-- Date: November 20, 2025

-- ============================================================================
-- Table: audit_log
-- Stores audit trail of all database changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name      VARCHAR(50) NOT NULL COMMENT 'Table where change occurred',
    record_id       INT NOT NULL COMMENT 'ID of the affected record',
    operation       VARCHAR(10) NOT NULL COMMENT 'Operation type: INSERT, UPDATE, DELETE',
    old_values      TEXT COMMENT 'JSON of old values (for UPDATE/DELETE)',
    new_values      TEXT COMMENT 'JSON of new values (for INSERT/UPDATE)',
    changed_by      VARCHAR(100) DEFAULT 'system' COMMENT 'User who made the change',
    changed_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When change occurred',
    ip_address      VARCHAR(45) COMMENT 'IP address of user (if applicable)',
    
    INDEX idx_audit_log_table (table_name),
    INDEX idx_audit_log_record (table_name, record_id),
    INDEX idx_audit_log_operation (operation),
    INDEX idx_audit_log_date (changed_at),
    INDEX idx_audit_log_user (changed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Audit trail for all database changes';


-- ============================================================================
-- Drop existing triggers first (if any)
-- ============================================================================
DROP TRIGGER IF EXISTS trg_families_after_insert;
DROP TRIGGER IF EXISTS trg_families_after_update;
DROP TRIGGER IF EXISTS trg_families_after_delete;
DROP TRIGGER IF EXISTS trg_payments_after_insert;
DROP TRIGGER IF EXISTS trg_payments_after_update;
DROP TRIGGER IF EXISTS trg_payments_after_delete;
DROP TRIGGER IF EXISTS trg_subscriptions_after_insert;
DROP TRIGGER IF EXISTS trg_subscriptions_after_update;
DROP TRIGGER IF EXISTS trg_subscriptions_after_delete;


-- ============================================================================
-- Triggers for families table
-- ============================================================================

DELIMITER $

CREATE TRIGGER trg_families_after_insert
AFTER INSERT ON families
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, new_values)
    VALUES (
        'families',
        NEW.id,
        'INSERT',
        JSON_OBJECT(
            'legacy_code', NEW.legacy_code,
            'last_name', NEW.last_name,
            'first_name', NEW.first_name,
            'phone', NEW.phone,
            'email', NEW.email,
            'is_active', NEW.is_active
        )
    );
END$

CREATE TRIGGER trg_families_after_update
AFTER UPDATE ON families
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
    VALUES (
        'families',
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'legacy_code', OLD.legacy_code,
            'last_name', OLD.last_name,
            'first_name', OLD.first_name,
            'phone', OLD.phone,
            'email', OLD.email,
            'is_active', OLD.is_active
        ),
        JSON_OBJECT(
            'legacy_code', NEW.legacy_code,
            'last_name', NEW.last_name,
            'first_name', NEW.first_name,
            'phone', NEW.phone,
            'email', NEW.email,
            'is_active', NEW.is_active
        )
    );
END$

CREATE TRIGGER trg_families_after_delete
AFTER DELETE ON families
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values)
    VALUES (
        'families',
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'legacy_code', OLD.legacy_code,
            'last_name', OLD.last_name,
            'first_name', OLD.first_name,
            'phone', OLD.phone,
            'email', OLD.email,
            'is_active', OLD.is_active
        )
    );
END$


-- ============================================================================
-- Triggers for payments table
-- ============================================================================

CREATE TRIGGER trg_payments_after_insert
AFTER INSERT ON payments
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, new_values)
    VALUES (
        'payments',
        NEW.id,
        'INSERT',
        JSON_OBJECT(
            'family_id', NEW.family_id,
            'receipt_no', NEW.receipt_no,
            'payment_date', NEW.payment_date,
            'total_amount', NEW.total_amount,
            'paid_amount', NEW.paid_amount,
            'status', NEW.status
        )
    );
END$

CREATE TRIGGER trg_payments_after_update
AFTER UPDATE ON payments
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
    VALUES (
        'payments',
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'family_id', OLD.family_id,
            'receipt_no', OLD.receipt_no,
            'payment_date', OLD.payment_date,
            'total_amount', OLD.total_amount,
            'paid_amount', OLD.paid_amount,
            'status', OLD.status
        ),
        JSON_OBJECT(
            'family_id', NEW.family_id,
            'receipt_no', NEW.receipt_no,
            'payment_date', NEW.payment_date,
            'total_amount', NEW.total_amount,
            'paid_amount', NEW.paid_amount,
            'status', NEW.status
        )
    );
END$

CREATE TRIGGER trg_payments_after_delete
AFTER DELETE ON payments
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values)
    VALUES (
        'payments',
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'family_id', OLD.family_id,
            'receipt_no', OLD.receipt_no,
            'payment_date', OLD.payment_date,
            'total_amount', OLD.total_amount,
            'paid_amount', OLD.paid_amount,
            'status', OLD.status
        )
    );
END$


-- ============================================================================
-- Triggers for subscriptions table
-- ============================================================================

CREATE TRIGGER trg_subscriptions_after_insert
AFTER INSERT ON subscriptions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, new_values)
    VALUES (
        'subscriptions',
        NEW.id,
        'INSERT',
        JSON_OBJECT(
            'family_id', NEW.family_id,
            'year', NEW.year,
            'start_date', NEW.start_date,
            'end_date', NEW.end_date,
            'status', NEW.status,
            'payment_id', NEW.payment_id
        )
    );
END$

CREATE TRIGGER trg_subscriptions_after_update
AFTER UPDATE ON subscriptions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values, new_values)
    VALUES (
        'subscriptions',
        NEW.id,
        'UPDATE',
        JSON_OBJECT(
            'family_id', OLD.family_id,
            'year', OLD.year,
            'start_date', OLD.start_date,
            'end_date', OLD.end_date,
            'status', OLD.status,
            'payment_id', OLD.payment_id
        ),
        JSON_OBJECT(
            'family_id', NEW.family_id,
            'year', NEW.year,
            'start_date', NEW.start_date,
            'end_date', NEW.end_date,
            'status', NEW.status,
            'payment_id', NEW.payment_id
        )
    );
END$

CREATE TRIGGER trg_subscriptions_after_delete
AFTER DELETE ON subscriptions
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, operation, old_values)
    VALUES (
        'subscriptions',
        OLD.id,
        'DELETE',
        JSON_OBJECT(
            'family_id', OLD.family_id,
            'year', OLD.year,
            'start_date', OLD.start_date,
            'end_date', OLD.end_date,
            'status', OLD.status,
            'payment_id', OLD.payment_id
        )
    );
END$

DELIMITER ;


-- ============================================================================
-- Mark migration as applied
-- ============================================================================
INSERT INTO schema_migrations (version, description)
VALUES (12, 'Create audit_log table with triggers for families, payments, subscriptions')
ON DUPLICATE KEY UPDATE description=description;
