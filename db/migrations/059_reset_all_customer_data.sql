-- Migration 059: FULL RESET of customer & transactional data (fresh start)
-- Deletes all clients and all transactional data, resets numbering to zero.
-- KEEPS: users/permissions, support_packages catalog, app_settings (org/SMTP/PDF/pricing).
-- Requested explicitly by the owner (test data). Numbering restarts from the beginning.

SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM client_package_hours;
DELETE FROM support_sessions;
DELETE FROM subscriptions;
DELETE FROM payments;
DELETE FROM families;
DELETE FROM audit_log;

ALTER TABLE client_package_hours AUTO_INCREMENT = 1;
ALTER TABLE support_sessions   AUTO_INCREMENT = 1;
ALTER TABLE subscriptions       AUTO_INCREMENT = 1;
ALTER TABLE payments            AUTO_INCREMENT = 1;
ALTER TABLE families            AUTO_INCREMENT = 1;
ALTER TABLE audit_log           AUTO_INCREMENT = 1;

SET FOREIGN_KEY_CHECKS = 1;

-- Restart numbering: next client code = 1, next receipt = ΑΠ-0001
UPDATE app_settings
SET receipt_counter = 0, subscription_counter = 0, family_counter = 0
WHERE id = 1;
