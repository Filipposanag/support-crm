-- Migration 034: Seed Default Auth Data
-- Default groups, permissions, and admin user
-- MariaDB 10.x compatible

-- ============================================================================
-- Insert Default User Groups
-- ============================================================================
INSERT IGNORE INTO user_groups (id, name, description, is_system) VALUES
(1, 'Διαχειριστές', 'Πλήρης πρόσβαση σε όλες τις λειτουργίες του συστήματος', 1),
(2, 'Χρήστες', 'Βασικές λειτουργίες - δημιουργία, επεξεργασία, προβολή (χωρίς διαγραφή και ρυθμίσεις)', 1),
(3, 'Προβολή', 'Μόνο ανάγνωση - προβολή δεδομένων χωρίς δυνατότητα τροποποίησης', 1);


-- ============================================================================
-- Insert All Permissions
-- ============================================================================

-- Families permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('families.view', 'Προβολή Οικογενειών', 'families', 'Δυνατότητα προβολής λίστας και λεπτομερειών οικογενειών'),
('families.create', 'Δημιουργία Οικογένειας', 'families', 'Δυνατότητα δημιουργίας νέας οικογένειας'),
('families.edit', 'Επεξεργασία Οικογένειας', 'families', 'Δυνατότητα επεξεργασίας στοιχείων οικογένειας'),
('families.delete', 'Διαγραφή Οικογένειας', 'families', 'Δυνατότητα διαγραφής οικογένειας'),
('families.export', 'Εξαγωγή Οικογενειών', 'families', 'Δυνατότητα εξαγωγής δεδομένων οικογενειών σε Excel/PDF');

-- Members permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('members.view', 'Προβολή Μελών', 'members', 'Δυνατότητα προβολής μελών οικογένειας'),
('members.create', 'Δημιουργία Μέλους', 'members', 'Δυνατότητα προσθήκης νέου μέλους'),
('members.edit', 'Επεξεργασία Μέλους', 'members', 'Δυνατότητα επεξεργασίας στοιχείων μέλους'),
('members.delete', 'Διαγραφή Μέλους', 'members', 'Δυνατότητα διαγραφής μέλους');

-- Payments permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('payments.view', 'Προβολή Πληρωμών', 'payments', 'Δυνατότητα προβολής λίστας και λεπτομερειών πληρωμών'),
('payments.create', 'Δημιουργία Πληρωμής', 'payments', 'Δυνατότητα καταχώρησης νέας πληρωμής'),
('payments.edit', 'Επεξεργασία Πληρωμής', 'payments', 'Δυνατότητα επεξεργασίας στοιχείων πληρωμής'),
('payments.delete', 'Διαγραφή Πληρωμής', 'payments', 'Δυνατότητα διαγραφής πληρωμής'),
('payments.export', 'Εξαγωγή Πληρωμών', 'payments', 'Δυνατότητα εξαγωγής δεδομένων πληρωμών σε Excel/PDF');

-- Subscriptions permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('subscriptions.view', 'Προβολή Συνδρομών', 'subscriptions', 'Δυνατότητα προβολής λίστας και λεπτομερειών συνδρομών'),
('subscriptions.create', 'Δημιουργία Συνδρομής', 'subscriptions', 'Δυνατότητα δημιουργίας νέας συνδρομής'),
('subscriptions.edit', 'Επεξεργασία Συνδρομής', 'subscriptions', 'Δυνατότητα επεξεργασίας στοιχείων συνδρομής'),
('subscriptions.delete', 'Διαγραφή Συνδρομής', 'subscriptions', 'Δυνατότητα διαγραφής συνδρομής'),
('subscriptions.cancel', 'Ακύρωση Συνδρομής', 'subscriptions', 'Δυνατότητα ακύρωσης ενεργής συνδρομής'),
('subscriptions.export', 'Εξαγωγή Συνδρομών', 'subscriptions', 'Δυνατότητα εξαγωγής δεδομένων συνδρομών σε Excel/PDF');

-- Reports permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('reports.view', 'Προβολή Αναφορών', 'reports', 'Δυνατότητα προβολής στατιστικών και αναφορών'),
('reports.export', 'Εξαγωγή Αναφορών', 'reports', 'Δυνατότητα εξαγωγής αναφορών σε Excel/PDF');

-- Settings permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('settings.view', 'Προβολή Ρυθμίσεων', 'settings', 'Δυνατότητα προβολής ρυθμίσεων εφαρμογής'),
('settings.edit', 'Επεξεργασία Ρυθμίσεων', 'settings', 'Δυνατότητα αλλαγής ρυθμίσεων εφαρμογής');

-- Users/Admin permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('users.view', 'Προβολή Χρηστών', 'users', 'Δυνατότητα προβολής λίστας χρηστών'),
('users.create', 'Δημιουργία Χρήστη', 'users', 'Δυνατότητα δημιουργίας νέου χρήστη'),
('users.edit', 'Επεξεργασία Χρήστη', 'users', 'Δυνατότητα επεξεργασίας στοιχείων χρήστη'),
('users.delete', 'Διαγραφή Χρήστη', 'users', 'Δυνατότητα διαγραφής χρήστη'),
('groups.manage', 'Διαχείριση Ομάδων', 'users', 'Δυνατότητα διαχείρισης ομάδων και δικαιωμάτων');

-- Import permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('import.csv', 'Εισαγωγή CSV', 'import', 'Δυνατότητα εισαγωγής δεδομένων από CSV'),
('import.backup', 'Επαναφορά Backup', 'import', 'Δυνατότητα επαναφοράς από αντίγραφο ασφαλείας');

-- Backup permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('backup.create', 'Δημιουργία Backup', 'backup', 'Δυνατότητα δημιουργίας αντιγράφου ασφαλείας'),
('backup.restore', 'Επαναφορά Backup', 'backup', 'Δυνατότητα επαναφοράς από αντίγραφο ασφαλείας');


-- ============================================================================
-- Assign Permissions to Groups
-- ============================================================================

-- Διαχειριστές: ALL permissions
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 1, id FROM permissions;

-- Χρήστες: Basic operations (no delete, no settings, no users)
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 2, id FROM permissions 
WHERE code IN (
    'families.view', 'families.create', 'families.edit', 'families.export',
    'members.view', 'members.create', 'members.edit',
    'payments.view', 'payments.create', 'payments.edit', 'payments.export',
    'subscriptions.view', 'subscriptions.create', 'subscriptions.edit', 'subscriptions.export',
    'reports.view', 'reports.export',
    'backup.create'
);

-- Προβολή: View only
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 3, id FROM permissions 
WHERE code IN (
    'families.view',
    'members.view',
    'payments.view',
    'subscriptions.view',
    'reports.view'
);


-- ============================================================================
-- Create Default Admin User
-- Password: admin123 (bcrypt hash)
-- IMPORTANT: Change this password immediately after first login!
-- ============================================================================
INSERT IGNORE INTO users (id, username, password_hash, email, first_name, last_name, group_id, is_active, is_system) VALUES
(1, 'admin', '$2b$12$r14lsthhV1bVY4TIEWisFeOPiV0B/YG2i0ljZyyoJNnHHV6Ie3Pe.', 'admin@localhost', 'Διαχειριστής', 'Συστήματος', 1, 1, 1);
