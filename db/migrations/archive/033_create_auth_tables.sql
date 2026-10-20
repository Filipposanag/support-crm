-- Migration 033: Create Authentication & Authorization Tables
-- SupportCRM User Management System
-- MariaDB 10.x compatible

-- ============================================================================
-- Table: user_groups
-- Stores user groups/roles with their descriptions
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_groups (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE COMMENT 'Group name (e.g., Διαχειριστές)',
    description     TEXT COMMENT 'Group description',
    is_system       TINYINT(1) DEFAULT 0 COMMENT 'System group (cannot be deleted)',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    INDEX idx_user_groups_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User groups/roles for access control';


-- ============================================================================
-- Table: users
-- Stores user accounts
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE COMMENT 'Login username',
    password_hash   VARCHAR(255) NOT NULL COMMENT 'Bcrypt hashed password',
    email           VARCHAR(100) COMMENT 'User email address',
    first_name      VARCHAR(100) COMMENT 'User first name',
    last_name       VARCHAR(100) COMMENT 'User last name',
    group_id        INT NOT NULL COMMENT 'Reference to user_groups',
    is_active       TINYINT(1) DEFAULT 1 COMMENT 'Account active status',
    is_system       TINYINT(1) DEFAULT 0 COMMENT 'System user (cannot be deleted)',
    last_login      DATETIME COMMENT 'Last successful login timestamp',
    failed_attempts INT DEFAULT 0 COMMENT 'Failed login attempts counter',
    locked_until    DATETIME COMMENT 'Account locked until this time',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE RESTRICT,
    
    INDEX idx_users_username (username),
    INDEX idx_users_email (email),
    INDEX idx_users_group (group_id),
    INDEX idx_users_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User accounts for authentication';


-- ============================================================================
-- Table: permissions
-- Stores available permissions/actions
-- ============================================================================
CREATE TABLE IF NOT EXISTS permissions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE COMMENT 'Permission code (e.g., families.create)',
    name            VARCHAR(100) NOT NULL COMMENT 'Display name (e.g., Δημιουργία Οικογένειας)',
    category        VARCHAR(50) NOT NULL COMMENT 'Category (e.g., families, payments)',
    description     TEXT COMMENT 'Permission description',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    
    INDEX idx_permissions_code (code),
    INDEX idx_permissions_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Available permissions for access control';


-- ============================================================================
-- Table: group_permissions
-- Links groups to their permissions (many-to-many)
-- ============================================================================
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id        INT NOT NULL COMMENT 'Reference to user_groups',
    permission_id   INT NOT NULL COMMENT 'Reference to permissions',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    
    PRIMARY KEY (group_id, permission_id),
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    
    INDEX idx_group_permissions_group (group_id),
    INDEX idx_group_permissions_permission (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Group to permission mappings';


-- ============================================================================
-- Table: user_sessions
-- Tracks user login sessions for auditing
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL COMMENT 'Reference to users',
    session_token   VARCHAR(255) NOT NULL UNIQUE COMMENT 'Unique session identifier',
    ip_address      VARCHAR(45) COMMENT 'Client IP address',
    user_agent      VARCHAR(255) COMMENT 'Client user agent',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Session start timestamp',
    expires_at      DATETIME NOT NULL COMMENT 'Session expiration timestamp',
    ended_at        DATETIME COMMENT 'Session end timestamp (logout)',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_user_sessions_user (user_id),
    INDEX idx_user_sessions_token (session_token),
    INDEX idx_user_sessions_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User login session tracking';
