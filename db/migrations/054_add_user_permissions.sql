-- Migration 054: Per-user permission overrides + Τεχνικοί baseline
-- Adds granular per-user permissions on top of the group (role) baseline.
-- Effective permissions = (group permissions) UNION (user 'grant') MINUS (user 'deny').
-- Admins (group Διαχειριστές) always bypass and keep full access.
-- MariaDB 10.x compatible

-- ============================================================================
-- Table: user_permissions
-- Per-user overrides on top of the group baseline
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id         INT NOT NULL COMMENT 'Reference to users',
    permission_id   INT NOT NULL COMMENT 'Reference to permissions',
    effect          ENUM('grant','deny') NOT NULL DEFAULT 'grant'
                    COMMENT 'grant = add on top of role, deny = remove from role',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',

    PRIMARY KEY (user_id, permission_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,

    INDEX idx_user_permissions_user (user_id),
    INDEX idx_user_permissions_permission (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Per-user permission overrides (grant/deny) on top of group baseline';


-- ============================================================================
-- Rename group 2 (Χρήστες) -> Τεχνικοί, to match the two-role model
-- ============================================================================
UPDATE user_groups
SET name = 'Τεχνικοί',
    description = 'Τεχνικοί υποστήριξης — πρόσβαση στην καθημερινή εργασία (πελάτες, συνεδρίες, αποδείξεις, RustDesk). Ο διαχειριστής προσαρμόζει τα δικαιώματα ανά χρήστη.'
WHERE id = 2;


-- ============================================================================
-- Reset the Τεχνικοί (group_id = 2) baseline to the agreed permission set
-- ============================================================================
DELETE FROM group_permissions WHERE group_id = 2;

INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 2, id FROM permissions WHERE code IN (
    -- Πελάτες: view/create/edit/export (όχι delete)
    'clients.view', 'clients.create', 'clients.edit', 'clients.export',
    -- Συνεδρίες: view/create/edit/export (όχι delete)
    'sessions.view', 'sessions.create', 'sessions.edit', 'sessions.export',
    -- Πακέτα: μόνο προβολή
    'packages.view',
    -- Πληρωμές/Παραστατικά: view + create (έκδοση απόδειξης)
    'payments.view', 'payments.create',
    -- Απομακρυσμένη υποστήριξη
    'rustdesk.launch'
);
