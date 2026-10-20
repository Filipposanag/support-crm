-- Migration 041: Update Permissions for Support CRM
-- Changes permission codes and names from "families" to "clients"
-- to match the Support CRM transformation

-- ============================================================================
-- Update Families Permissions to Clients Permissions
-- ============================================================================

-- Update permission codes and names
UPDATE permissions 
SET code = 'clients.view',
    name = 'Προβολή Πελατών',
    category = 'clients',
    description = 'Δυνατότητα προβολής λίστας και λεπτομερειών πελατών'
WHERE code = 'families.view';

UPDATE permissions 
SET code = 'clients.create',
    name = 'Δημιουργία Πελάτη',
    category = 'clients',
    description = 'Δυνατότητα δημιουργίας νέου πελάτη'
WHERE code = 'families.create';

UPDATE permissions 
SET code = 'clients.edit',
    name = 'Επεξεργασία Πελάτη',
    category = 'clients',
    description = 'Δυνατότητα επεξεργασίας στοιχείων πελάτη'
WHERE code = 'families.edit';

UPDATE permissions 
SET code = 'clients.delete',
    name = 'Διαγραφή Πελάτη',
    category = 'clients',
    description = 'Δυνατότητα διαγραφής πελάτη'
WHERE code = 'families.delete';

UPDATE permissions 
SET code = 'clients.export',
    name = 'Εξαγωγή Πελατών',
    category = 'clients',
    description = 'Δυνατότητα εξαγωγής δεδομένων πελατών σε Excel/PDF'
WHERE code = 'families.export';


-- ============================================================================
-- Add New Support CRM Specific Permissions
-- ============================================================================

-- Sessions permissions (for support sessions)
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('sessions.view', 'Προβολή Sessions', 'sessions', 'Δυνατότητα προβολής λίστας και λεπτομερειών sessions'),
('sessions.create', 'Δημιουργία Session', 'sessions', 'Δυνατότητα δημιουργίας νέου session'),
('sessions.edit', 'Επεξεργασία Session', 'sessions', 'Δυνατότητα επεξεργασίας στοιχείων session'),
('sessions.delete', 'Διαγραφή Session', 'sessions', 'Δυνατότητα διαγραφής session'),
('sessions.export', 'Εξαγωγή Sessions', 'sessions', 'Δυνατότητα εξαγωγής δεδομένων sessions σε Excel/PDF');

-- Support packages permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('packages.view', 'Προβολή Πακέτων', 'packages', 'Δυνατότητα προβολής πακέτων υποστήριξης'),
('packages.manage', 'Διαχείριση Πακέτων', 'packages', 'Δυνατότητα δημιουργίας και επεξεργασίας πακέτων υποστήριξης');

-- RustDesk permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('rustdesk.launch', 'Εκκίνηση RustDesk', 'support', 'Δυνατότητα εκκίνησης RustDesk για απομακρυσμένη υποστήριξη');


-- ============================================================================
-- Assign New Permissions to Existing Groups
-- ============================================================================

-- Διαχειριστές: ALL new permissions
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 1, id FROM permissions 
WHERE code IN (
    'sessions.view', 'sessions.create', 'sessions.edit', 'sessions.delete', 'sessions.export',
    'packages.view', 'packages.manage',
    'rustdesk.launch'
);

-- Χρήστες: Basic operations (no delete)
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 2, id FROM permissions 
WHERE code IN (
    'sessions.view', 'sessions.create', 'sessions.edit', 'sessions.export',
    'packages.view',
    'rustdesk.launch'
);

-- Προβολή: View only
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 3, id FROM permissions 
WHERE code IN (
    'sessions.view',
    'packages.view'
);
