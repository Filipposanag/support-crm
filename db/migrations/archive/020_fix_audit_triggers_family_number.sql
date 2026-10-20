-- Migration 020: Fix audit triggers after family_number removal
-- Description: Update audit triggers to remove references to family_number column
-- Date: November 21, 2025

-- ============================================================================
-- Drop old triggers for families table
-- ============================================================================

DROP TRIGGER IF EXISTS trg_families_after_insert;
DROP TRIGGER IF EXISTS trg_families_after_update;
DROP TRIGGER IF EXISTS trg_families_after_delete;


-- ============================================================================
-- Recreate triggers for families table (without family_number)
-- ============================================================================

DELIMITER $$

-- Trigger: After INSERT on families
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
END$$

-- Trigger: After UPDATE on families
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
END$$

-- Trigger: After DELETE on families
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
END$$

DELIMITER ;


-- ============================================================================
-- Mark migration as applied
-- ============================================================================
INSERT INTO schema_migrations (version, description)
VALUES (20, 'Fix audit triggers after family_number removal')
ON DUPLICATE KEY UPDATE description=description;
