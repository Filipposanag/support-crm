-- Migration 060: Dedicated permission for the «Λήξεις Πακέτων» screen (client package expirations)
-- The screen (ui/widgets/client_packages_view.py, view_id 'client_packages') previously had no
-- permission of its own. Add one under the «Πακέτα» category and grant it to Διαχειριστές (1)
-- and Τεχνικοί (2), so technicians get access and admins can toggle it per-user from «Επεξεργασία Χρήστη».

INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('packages.expirations', 'Λήξεις Πακέτων', 'packages',
 'Πρόσβαση στην οθόνη «Λήξεις Πακέτων» (ενεργά/ληγμένα πακέτα πελατών & υπενθυμίσεις λήξης)');

-- Baseline grant: Διαχειριστές (group 1) + Τεχνικοί (group 2)
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT g.gid, p.id
FROM permissions p
JOIN (SELECT 1 AS gid UNION SELECT 2 AS gid) g
WHERE p.code = 'packages.expirations';
