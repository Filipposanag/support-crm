-- ============================================================================
-- Support CRM Database Schema (Fixed & Complete)
-- MariaDB 10.x compatible
-- Character set: UTF-8 (utf8mb4)
-- Version: 3.2 (Fixed - January 2026)
-- ============================================================================

-- ============================================================================
-- Table: families (clients)
-- Stores client information (families/individuals/businesses)
-- ============================================================================
CREATE TABLE IF NOT EXISTS families (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    legacy_code     INT NOT NULL COMMENT 'Client code (used for auto-numbering)',
    last_name       VARCHAR(100) NOT NULL COMMENT 'Client last name (required)',
    first_name      VARCHAR(100) NOT NULL COMMENT 'Client first name (required)',
    company_name    VARCHAR(200) DEFAULT '' COMMENT 'Company/Business name for corporate clients',
    father_name     VARCHAR(100) COMMENT 'Father name (Όνομα Πατρός) - legacy field',
    spouse_name     VARCHAR(100) COMMENT 'Spouse name - legacy field',
    spouse_maiden_name VARCHAR(100) COMMENT 'Spouse maiden name (Γένος Συζύγου) - legacy field',
    is_divorced     TINYINT(1) DEFAULT 0 COMMENT 'Divorced status (1=yes, 0=no) - legacy field',
    spouse_deceased TINYINT(1) DEFAULT 0 COMMENT 'Widowed/Χήρος-α (1=yes, 0=no) - legacy field',
    national_id     VARCHAR(30) COMMENT 'National ID (ADT)',
    afm             VARCHAR(20) DEFAULT '' COMMENT 'Client Tax ID (ΑΦΜ) - required for invoices',
    doy             VARCHAR(100) DEFAULT '' COMMENT 'Client tax office (ΔΟΥ) - for invoices',
    profession      VARCHAR(100) COMMENT 'Profession',
    address         VARCHAR(200) COMMENT 'Street address',
    city            VARCHAR(100) COMMENT 'City',
    postal_code     VARCHAR(20) COMMENT 'Postal code',
    phone           VARCHAR(50) DEFAULT '' COMMENT 'Phone number',
    mobile          VARCHAR(50) DEFAULT '' COMMENT 'Mobile number',
    email           VARCHAR(100) DEFAULT '' COMMENT 'Email address',
    birth_date      DATE COMMENT 'Birth date',
    members_count   INT DEFAULT 0 COMMENT 'Number of family members - legacy field',
    is_association_member TINYINT(1) DEFAULT 0 COMMENT 'Association member - allows free subscription',
    notes           TEXT COMMENT 'General notes',
    notes_support   TEXT COMMENT 'Support-specific notes (technical issues, solutions, etc.)',
    rustdesk_id     VARCHAR(50) DEFAULT '' COMMENT 'RustDesk ID for remote support',
    rustdesk_password VARCHAR(100) DEFAULT '' COMMENT 'RustDesk password (optional)',
    support_plan    ENUM('hourly', 'monthly', 'yearly', 'custom') DEFAULT 'hourly' COMMENT 'Support billing plan type',
    hourly_rate     DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Hourly support rate in EUR',
    monthly_rate    DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Monthly support rate in EUR',
    is_active       TINYINT(1) DEFAULT 1 COMMENT 'Active status (1=active, 0=inactive)',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Indexes for performance
    UNIQUE KEY uq_families_legacy_code (legacy_code),
    INDEX idx_families_name (last_name, first_name),
    INDEX idx_families_company_name (company_name),
    INDEX idx_families_national_id (national_id),
    INDEX idx_families_active (is_active),
    INDEX idx_families_rustdesk_id (rustdesk_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Client records (families/individuals/businesses) - Support CRM';


-- ============================================================================
-- Table: members
-- Stores individual family member information
-- ============================================================================
CREATE TABLE IF NOT EXISTS members (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    family_id           INT NOT NULL COMMENT 'Reference to families table',
    legacy_family_code  INT NOT NULL COMMENT 'Legacy CODE from members.csv',
    inner_no            INT NOT NULL COMMENT 'Member number within family (ANO)',
    reg_date            DATE COMMENT 'Registration date',
    first_name          VARCHAR(100) NOT NULL COMMENT 'Member first name (required)',
    last_name           VARCHAR(100) COMMENT 'Member last name',
    mother_name         VARCHAR(100) COMMENT 'Mother name (Όνομα Μητρός)',
    national_id         VARCHAR(30) COMMENT 'National ID (ADT)',
    birth_date          DATE COMMENT 'Birth date',
    profession          VARCHAR(100) COMMENT 'Profession',
    married             TINYINT(1) DEFAULT 0 COMMENT 'Marital status (1=married, 0=single)',
    marriage_date       DATE COMMENT 'Marriage date',
    is_active           TINYINT(1) DEFAULT 1 COMMENT 'Active status',
    is_deceased         TINYINT(1) DEFAULT 0 COMMENT 'Deceased status (Αποθανών/ούσα)',
    is_disabled         TINYINT(1) DEFAULT 0 COMMENT 'Disabled/AMEA status',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Foreign key constraint
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_members_family (family_id),
    INDEX idx_members_name (last_name, first_name),
    INDEX idx_members_national_id (national_id),
    INDEX idx_members_legacy (legacy_family_code, inner_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Individual family member records';


-- ============================================================================
-- Table: payments
-- Stores payment and subscription information
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    family_id           INT NOT NULL COMMENT 'Reference to families table',
    legacy_code         INT COMMENT 'Legacy CODE from report.csv',
    legacy_pcode        INT NULL COMMENT 'Legacy PCODE from report.csv (nullable for new payments)',
    payment_date        DATE NOT NULL COMMENT 'Payment date (required)',
    payment_time        TIME COMMENT 'Payment time',
    description         VARCHAR(255) COMMENT 'Payment description',
    receipt_no          VARCHAR(50) COMMENT 'Receipt number (auto-generated)',
    document_type       VARCHAR(20) DEFAULT 'receipt' COMMENT 'Issued document: receipt (Απόδειξη) or invoice (Τιμολόγιο)',
    vat_rate            DECIMAL(5,2) DEFAULT 0.00 COMMENT 'VAT % applied at issue time (snapshot)',
    subscription_code   VARCHAR(50) COMMENT 'Subscription code (auto-generated)',
    support_package     ENUM('hourly', 'monthly', 'yearly', 'custom') DEFAULT NULL COMMENT 'Support package type purchased with this payment',
    remarks             TEXT COMMENT 'Additional remarks',
    total_amount        DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Total amount due',
    paid_amount         DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Amount paid',
    remaining_amount    DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Remaining amount (calculated)',
    status              VARCHAR(20) DEFAULT 'UNPAID' COMMENT 'Payment status: PAID, PARTIAL, UNPAID',
    year                INT COMMENT 'Payment year (extracted from payment_date)',
    subscription_start_date DATE COMMENT 'Subscription start date',
    subscription_end_date DATE COMMENT 'Subscription end date',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Foreign key constraint
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_payments_family (family_id),
    INDEX idx_payments_date (payment_date),
    INDEX idx_payments_year (year),
    INDEX idx_payments_status (status),
    INDEX idx_payments_receipt_no (receipt_no),
    INDEX idx_payments_subscription_code (subscription_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Payment and subscription records';


-- ============================================================================
-- Table: subscriptions
-- Stores subscription records linked to payments
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    family_id       INT NOT NULL COMMENT 'Reference to families table',
    year            INT NOT NULL COMMENT 'Subscription year',
    start_date      DATE NOT NULL COMMENT 'Subscription start date',
    end_date        DATE NOT NULL COMMENT 'Subscription end date',
    status          VARCHAR(20) DEFAULT 'ACTIVE' COMMENT 'Subscription status: ACTIVE, EXPIRED, CANCELLED',
    payment_id      INT NOT NULL COMMENT 'Reference to payment (receipt) that created this subscription',
    subscription_code VARCHAR(50) COMMENT 'Subscription code (copied from payment)',
    total_amount    DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Total subscription amount',
    paid_amount     DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Amount paid',
    remaining_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Remaining amount',
    notes           TEXT COMMENT 'Additional notes',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Foreign key constraints
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
    
    -- Indexes for performance
    INDEX idx_subscriptions_family (family_id),
    INDEX idx_subscriptions_year (year),
    INDEX idx_subscriptions_status (status),
    INDEX idx_subscriptions_payment (payment_id),
    INDEX idx_subscriptions_code (subscription_code),
    INDEX idx_subscriptions_dates (start_date, end_date),
    UNIQUE KEY uq_subscriptions_family_year (family_id, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Subscription records linked to payments';


-- ============================================================================
-- Table: support_packages
-- Stores support packages with pricing and features
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT 'Package name (e.g., "Βασικό Πακέτο")',
    package_type ENUM('hourly', 'monthly', 'yearly', 'custom') NOT NULL COMMENT 'Package type',
    description TEXT COMMENT 'Package description',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Package price in EUR',
    duration_months INT DEFAULT NULL COMMENT 'Duration in months (for subscription packages)',
    prepaid_hours DECIMAL(10,2) DEFAULT NULL COMMENT 'Prepaid hours included in package',
    features TEXT COMMENT 'Package features (JSON or text)',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Active status',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_package_type (package_type),
    INDEX idx_is_active (is_active),
    UNIQUE KEY uk_package_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support packages with pricing and features';


-- ============================================================================
-- Table: client_package_hours
-- Tracks prepaid hours per client from support packages
-- ============================================================================
CREATE TABLE IF NOT EXISTS client_package_hours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL COMMENT 'Client (family) ID',
    package_id INT NOT NULL COMMENT 'Support package ID',
    payment_id INT DEFAULT NULL COMMENT 'Payment ID that purchased the hours',
    total_hours DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Total prepaid hours purchased',
    used_hours DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Hours used from sessions',
    purchase_date DATE NOT NULL COMMENT 'Date hours were purchased',
    expiry_date DATE DEFAULT NULL COMMENT 'Expiry date for hours (NULL = no expiry)',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Active status',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (client_id) REFERENCES families(id) ON DELETE CASCADE,
    FOREIGN KEY (package_id) REFERENCES support_packages(id) ON DELETE RESTRICT,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    
    INDEX idx_client_id (client_id),
    INDEX idx_package_id (package_id),
    INDEX idx_is_active (is_active),
    INDEX idx_expiry_date (expiry_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tracks prepaid hours per client from support packages';


-- ============================================================================
-- Table: sessions
-- Stores support session records for billing and tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    client_id           INT NOT NULL COMMENT 'Reference to families (clients)',
    session_type        ENUM('remote', 'onsite', 'phone') DEFAULT 'remote' COMMENT 'Type of support session',
    start_time          DATETIME NOT NULL COMMENT 'Session start time',
    end_time            DATETIME COMMENT 'Session end time',
    duration_minutes    INT DEFAULT 0 COMMENT 'Session duration in minutes',
    duration_seconds    INT DEFAULT 0 COMMENT 'Additional seconds for precise timing',
    technician          VARCHAR(100) COMMENT 'Technician name',
    description         TEXT COMMENT 'Session description/notes',
    issue_summary       TEXT COMMENT 'Brief summary of the issue',
    status              ENUM('active', 'completed', 'cancelled') DEFAULT 'active' COMMENT 'Session status',
    billed_amount       DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Amount billed for this session',
    payment_id          INT COMMENT 'Reference to payment if session is billed',
    is_billable         TINYINT(1) DEFAULT 1 COMMENT 'Whether session is billable',
    resolution_notes    TEXT COMMENT 'Notes about how the issue was resolved',
    customer_satisfaction INT COMMENT 'Customer satisfaction rating (1-5)',
    follow_up_required  TINYINT(1) DEFAULT 0 COMMENT 'Whether follow-up is required',
    follow_up_date      DATE COMMENT 'Scheduled follow-up date',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (client_id) REFERENCES families(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    
    INDEX idx_sessions_client (client_id),
    INDEX idx_sessions_start_time (start_time),
    INDEX idx_sessions_status (status),
    INDEX idx_sessions_type (session_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support session tracking for clients';


-- ============================================================================
-- Table: support_sessions (alias for sessions - for compatibility)
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_sessions (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    client_id           INT NOT NULL COMMENT 'Reference to families (clients)',
    session_type        ENUM('remote', 'onsite', 'phone') DEFAULT 'remote' COMMENT 'Type of support session',
    start_time          DATETIME NOT NULL COMMENT 'Session start time',
    end_time            DATETIME COMMENT 'Session end time',
    duration_minutes    INT DEFAULT 0 COMMENT 'Session duration in minutes',
    duration_seconds    INT DEFAULT 0 COMMENT 'Additional seconds for precise timing',
    rustdesk_session_id VARCHAR(100) COMMENT 'RustDesk session identifier',
    technician          VARCHAR(100) COMMENT 'Technician name',
    description         TEXT COMMENT 'Session description/notes',
    issue_summary       TEXT COMMENT 'Brief summary of the issue',
    status              ENUM('active', 'completed', 'cancelled') DEFAULT 'active' COMMENT 'Session status',
    billed_amount       DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Amount billed for this session',
    payment_id          INT COMMENT 'Reference to payment if session is billed',
    is_billable         TINYINT(1) DEFAULT 1 COMMENT 'Whether session is billable',
    resolution_notes    TEXT COMMENT 'Notes about how the issue was resolved',
    customer_satisfaction INT COMMENT 'Customer satisfaction rating (1-5)',
    follow_up_required  TINYINT(1) DEFAULT 0 COMMENT 'Whether follow-up is required',
    follow_up_date      DATE COMMENT 'Scheduled follow-up date',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp',
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    FOREIGN KEY (client_id) REFERENCES families(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL,
    
    INDEX idx_support_sessions_client (client_id),
    INDEX idx_support_sessions_start_time (start_time),
    INDEX idx_support_sessions_status (status),
    INDEX idx_support_sessions_type (session_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support session tracking for clients (alias table)';


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
    plain_password  VARCHAR(255) DEFAULT NULL COMMENT 'Plaintext password (admin-only visibility, demo)',
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
    code            VARCHAR(50) NOT NULL UNIQUE COMMENT 'Permission code (e.g., clients.create)',
    name            VARCHAR(100) NOT NULL COMMENT 'Display name (e.g., Δημιουργία Πελάτη)',
    category        VARCHAR(50) NOT NULL COMMENT 'Category (e.g., clients, payments)',
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


-- ============================================================================
-- Table: security_settings
-- Security and authentication settings
-- ============================================================================
CREATE TABLE IF NOT EXISTS security_settings (
    id                      INT PRIMARY KEY DEFAULT 1,
    session_timeout_minutes INT DEFAULT 60 COMMENT 'Session timeout in minutes',
    max_failed_attempts     INT DEFAULT 5 COMMENT 'Max failed login attempts before lockout',
    lockout_duration_minutes INT DEFAULT 30 COMMENT 'Account lockout duration in minutes',
    password_min_length     INT DEFAULT 6 COMMENT 'Minimum password length',
    require_password_change TINYINT(1) DEFAULT 0 COMMENT 'Force password change on first login',
    enable_audit_log        TINYINT(1) DEFAULT 1 COMMENT 'Enable audit logging',
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Security and authentication settings';


-- ============================================================================
-- Table: app_settings
-- Stores application settings, organization info, and configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS app_settings (
    id               INT PRIMARY KEY DEFAULT 1 COMMENT 'Single row table (always id=1)',
    org_name         VARCHAR(200) COMMENT 'Organization full name',
    org_short_name   VARCHAR(100) COMMENT 'Organization short name/abbreviation',
    org_address      VARCHAR(200) COMMENT 'Organization street address',
    org_city         VARCHAR(100) COMMENT 'Organization city',
    org_postal_code  VARCHAR(20) COMMENT 'Organization postal code',
    org_phone        VARCHAR(50) COMMENT 'Organization phone number',
    org_email        VARCHAR(100) COMMENT 'Organization email address',
    org_afm          VARCHAR(20) DEFAULT '' COMMENT 'Organization Tax ID (AFM)',
    
    pdf_title        VARCHAR(200) COMMENT 'Default PDF document title',
    pdf_footer       TEXT COMMENT 'Default PDF footer text (IBAN, contact info, etc.)',
    pdf_logo_path    VARCHAR(255) COMMENT 'Path to organization logo image file',
    
    -- Separate PDF settings per document type
    pdf_payment_title VARCHAR(200) DEFAULT 'Απόδειξη Πληρωμής' COMMENT 'PDF title for payment receipts',
    pdf_payment_footer TEXT COMMENT 'PDF footer for payment receipts',
    pdf_subscription_title VARCHAR(200) DEFAULT 'Βεβαίωση Συνδρομής' COMMENT 'PDF title for subscription certificates',
    pdf_subscription_footer TEXT COMMENT 'PDF footer for subscription certificates',
    
    -- PDF Template JSON data (visual editor)
    pdf_template_family TEXT DEFAULT NULL COMMENT 'JSON data for family certificate PDF template',
    pdf_template_payment TEXT DEFAULT NULL COMMENT 'JSON data for payment receipt PDF template',
    pdf_template_subscription TEXT DEFAULT NULL COMMENT 'JSON data for subscription certificate PDF template',
    
    families_visible_columns TEXT COMMENT 'JSON array of visible column keys for families view',
    families_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for families view',
    payments_visible_columns TEXT COMMENT 'JSON array of visible column keys for payments view',
    payments_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for payments view',
    subscriptions_visible_columns TEXT COMMENT 'JSON array of visible column keys for subscriptions view',
    subscriptions_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for subscriptions view',
    reports_visible_columns TEXT COMMENT 'JSON array of visible column keys for reports view',
    reports_columns_locked TINYINT(1) DEFAULT 0 COMMENT 'Lock column widths for reports view',
    
    -- Search Field Preferences
    families_search_fields TEXT DEFAULT NULL COMMENT 'JSON array of search fields for families view',
    payments_search_fields TEXT DEFAULT NULL COMMENT 'JSON array of search fields for payments view',
    subscriptions_search_fields TEXT DEFAULT NULL COMMENT 'JSON array of search fields for subscriptions view',
    reports_search_fields TEXT DEFAULT NULL COMMENT 'JSON array of search fields for reports view',
    
    -- SMTP Server Settings
    smtp_host        VARCHAR(255) DEFAULT '' COMMENT 'SMTP server hostname',
    smtp_port        INT DEFAULT 587 COMMENT 'SMTP server port',
    smtp_use_tls     TINYINT(1) DEFAULT 1 COMMENT 'Use TLS for SMTP connection',
    smtp_username    VARCHAR(255) DEFAULT '' COMMENT 'SMTP authentication username',
    smtp_password    VARCHAR(255) DEFAULT '' COMMENT 'SMTP authentication password',
    smtp_from_email  VARCHAR(255) DEFAULT '' COMMENT 'From email address',
    smtp_from_name   VARCHAR(255) DEFAULT '' COMMENT 'From name',
    
    -- Subscription Notification Settings
    days_before_expiration INT DEFAULT 30 COMMENT 'Days before expiration to highlight',
    highlight_enabled TINYINT(1) DEFAULT 1 COMMENT 'Enable subscription expiration highlighting',
    color_expiring   VARCHAR(20) DEFAULT '#FFA500' COMMENT 'Color for expiring subscriptions',
    color_expired    VARCHAR(20) DEFAULT '#FF0000' COMMENT 'Color for expired subscriptions',
    
    -- Email Receipt Settings
    email_receipt_subject VARCHAR(255) DEFAULT 'Απόδειξη Πληρωμής' COMMENT 'Default email receipt subject',
    email_receipt_body TEXT COMMENT 'Default email receipt body template',
    
    -- Email Subscription Reminder Settings
    email_subscription_subject VARCHAR(255) DEFAULT 'Υπενθύμιση Συνδρομής' COMMENT 'Default email subscription reminder subject',
    email_subscription_body TEXT COMMENT 'Default email subscription reminder body template',
    
    -- Email Family Certificate Settings
    email_certificate_subject VARCHAR(255) DEFAULT 'Βεβαίωση Εγγραφής' COMMENT 'Default email certificate subject',
    email_certificate_body TEXT COMMENT 'Default email certificate body template',
    
    -- License Management
    license_key VARCHAR(255) DEFAULT '' COMMENT 'License activation key',
    license_owner VARCHAR(200) DEFAULT '' COMMENT 'License owner name',
    license_start_date DATE NULL COMMENT 'License activation date',
    license_end_date DATE NULL COMMENT 'License expiration date',
    license_status VARCHAR(20) DEFAULT 'none' COMMENT 'License status: active, expired, none',
    last_online_validation DATETIME NULL COMMENT 'Last successful online license validation',
    last_validation_attempt DATETIME NULL COMMENT 'Last license validation attempt (success or fail)',
    offline_since DATETIME NULL COMMENT 'When the app went offline (first failed validation)',
    
    -- Auto-Numbering Settings
    receipt_counter INT DEFAULT 1 COMMENT 'Next receipt number',
    subscription_counter INT DEFAULT 1 COMMENT 'Next subscription number',
    family_counter INT DEFAULT 1 COMMENT 'Next family number (legacy_code)',
    receipt_prefix VARCHAR(20) DEFAULT 'ΑΠ' COMMENT 'Receipt number prefix',
    subscription_prefix VARCHAR(20) DEFAULT 'ΣΥΝ' COMMENT 'Subscription number prefix',
    invoice_counter INT DEFAULT 1 COMMENT 'Next invoice number',
    invoice_prefix VARCHAR(20) DEFAULT 'ΤΠΥ' COMMENT 'Invoice number prefix',
    vat_rate DECIMAL(5,2) DEFAULT 24.00 COMMENT 'Default VAT rate (%) for documents (0 = no VAT breakdown)',
    
    -- Update Checker Settings
    auto_check_updates TINYINT(1) DEFAULT 1 COMMENT 'Enable automatic update checking on startup',
    
    -- RustDesk Settings (Support CRM)
    rustdesk_server_host VARCHAR(255) DEFAULT '' COMMENT 'RustDesk server hostname',
    rustdesk_server_port INT DEFAULT 21116 COMMENT 'RustDesk server port',
    rustdesk_api_key VARCHAR(255) DEFAULT '' COMMENT 'RustDesk API key',
    rustdesk_relay_server VARCHAR(255) DEFAULT '' COMMENT 'RustDesk relay server',
    default_hourly_rate DECIMAL(10,2) DEFAULT 40.00 COMMENT 'Default hourly support rate in EUR',
    default_monthly_rate DECIMAL(10,2) DEFAULT 200.00 COMMENT 'Default monthly support rate in EUR',
    session_rounding_minutes INT DEFAULT 15 COMMENT 'Session time rounding in minutes',
    
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    INDEX idx_app_settings_license_status (license_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Application settings and organization configuration';


-- ============================================================================
-- Table: pdf_templates
-- Stores PDF template configurations for visual editor
-- ============================================================================
CREATE TABLE IF NOT EXISTS pdf_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_type VARCHAR(50) NOT NULL UNIQUE COMMENT 'Template type: family, payment, subscription',
    template_name VARCHAR(255) NOT NULL COMMENT 'Display name of template',
    page_width DECIMAL(10,2) DEFAULT 595.0 COMMENT 'Page width in points (A4)',
    page_height DECIMAL(10,2) DEFAULT 842.0 COMMENT 'Page height in points (A4)',
    margin_top DECIMAL(10,2) DEFAULT 50.0 COMMENT 'Top margin in points',
    margin_bottom DECIMAL(10,2) DEFAULT 50.0 COMMENT 'Bottom margin in points',
    margin_left DECIMAL(10,2) DEFAULT 50.0 COMMENT 'Left margin in points',
    margin_right DECIMAL(10,2) DEFAULT 50.0 COMMENT 'Right margin in points',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='PDF template configurations for visual editor';


-- ============================================================================
-- Table: pdf_template_elements
-- Stores element positions and properties for PDF templates
-- ============================================================================
CREATE TABLE IF NOT EXISTS pdf_template_elements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_id INT NOT NULL COMMENT 'Reference to pdf_templates',
    element_type VARCHAR(50) NOT NULL COMMENT 'Element type: logo, title, org_name, date, content, footer, signature, amount, custom_text, custom_field',
    element_name VARCHAR(255) NOT NULL COMMENT 'Display name of element',
    pos_x DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'X position in points',
    pos_y DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT 'Y position in points',
    width DECIMAL(10,2) DEFAULT 100 COMMENT 'Element width in points',
    height DECIMAL(10,2) DEFAULT 30 COMMENT 'Element height in points',
    font_size INT DEFAULT 12 COMMENT 'Font size in points',
    font_bold TINYINT(1) DEFAULT 0 COMMENT 'Bold text',
    font_italic TINYINT(1) DEFAULT 0 COMMENT 'Italic text',
    text_align VARCHAR(20) DEFAULT 'left' COMMENT 'Text alignment: left, center, right',
    visible TINYINT(1) DEFAULT 1 COMMENT 'Element visibility',
    z_order INT DEFAULT 0 COMMENT 'Z-order for layering',
    custom_text TEXT COMMENT 'Custom text or placeholder template',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES pdf_templates(id) ON DELETE CASCADE,
    INDEX idx_pdf_elements_template (template_id),
    INDEX idx_pdf_elements_type (element_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='PDF template element positions and properties';


-- ============================================================================
-- Table: schema_migrations
-- Tracks applied database migrations
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INT PRIMARY KEY COMMENT 'Migration version number',
    description     VARCHAR(255) NOT NULL COMMENT 'Migration description',
    applied_at      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'When migration was applied',
    
    INDEX idx_schema_migrations_applied (applied_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Database migration tracking';


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
    
    -- Indexes for performance
    INDEX idx_audit_log_table (table_name),
    INDEX idx_audit_log_record (table_name, record_id),
    INDEX idx_audit_log_operation (operation),
    INDEX idx_audit_log_date (changed_at),
    INDEX idx_audit_log_user (changed_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Audit trail for all database changes';


-- ============================================================================
-- Table: import_logs
-- Stores CSV import operation logs
-- ============================================================================
CREATE TABLE IF NOT EXISTS import_logs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    file_name       VARCHAR(255) NOT NULL COMMENT 'Name of imported file',
    file_type       VARCHAR(50) NOT NULL COMMENT 'Type: client, members, report',
    imported_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Import timestamp',
    rows_total      INT DEFAULT 0 COMMENT 'Total rows in file',
    rows_success    INT DEFAULT 0 COMMENT 'Successfully imported rows',
    rows_failed     INT DEFAULT 0 COMMENT 'Failed rows',
    error_log       TEXT COMMENT 'Error details (JSON or text)',
    duration_seconds DECIMAL(10,2) COMMENT 'Import duration in seconds',
    
    -- Indexes for performance
    INDEX idx_import_logs_type (file_type),
    INDEX idx_import_logs_date (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='CSV import operation logs';


-- ============================================================================
-- INITIAL DATA / SEED DATA
-- ============================================================================

-- Insert default app_settings row
INSERT INTO app_settings (
    id, org_name, org_short_name, pdf_title, pdf_payment_title, pdf_subscription_title,
    receipt_counter, subscription_counter, family_counter, receipt_prefix, subscription_prefix, invoice_counter, invoice_prefix, vat_rate,
    auto_check_updates, default_hourly_rate, default_monthly_rate, session_rounding_minutes
) VALUES (
    1, 'Support CRM', 'Support CRM', 'Βεβαίωση Συνδρομής', 'Απόδειξη Πληρωμής', 'Βεβαίωση Συνδρομής',
    1, 1, 1, 'ΑΠ', 'ΣΥΝ', 1, 'ΤΠΥ', 24.00,
    0, 40.00, 200.00, 15
) ON DUPLICATE KEY UPDATE id=id;

-- Insert default security settings
INSERT INTO security_settings (id) VALUES (1) ON DUPLICATE KEY UPDATE id=id;

-- Insert default user groups
INSERT IGNORE INTO user_groups (id, name, description, is_system) VALUES
(1, 'Διαχειριστές', 'Πλήρης πρόσβαση σε όλες τις λειτουργίες του συστήματος', 1),
(2, 'Χρήστες', 'Βασικές λειτουργίες - δημιουργία, επεξεργασία, προβολή (χωρίς διαγραφή και ρυθμίσεις)', 1),
(3, 'Προβολή', 'Μόνο ανάγνωση - προβολή δεδομένων χωρίς δυνατότητα τροποποίησης', 1);

-- Insert default admin user (password: admin123)
INSERT IGNORE INTO users (id, username, password_hash, email, first_name, last_name, group_id, is_active, is_system) VALUES
(1, 'admin', '$2b$12$r14lsthhV1bVY4TIEWisFeOPiV0B/YG2i0ljZyyoJNnHHV6Ie3Pe.', 'admin@localhost', 'Διαχειριστής', 'Συστήματος', 1, 1, 1);

-- Insert basic permissions
INSERT IGNORE INTO permissions (code, name, category, description) VALUES
('clients.view', 'Προβολή Πελατών', 'clients', 'Δυνατότητα προβολής λίστας και λεπτομερειών πελατών'),
('clients.create', 'Δημιουργία Πελάτη', 'clients', 'Δυνατότητα δημιουργίας νέου πελάτη'),
('clients.edit', 'Επεξεργασία Πελάτη', 'clients', 'Δυνατότητα επεξεργασίας στοιχείων πελάτη'),
('clients.delete', 'Διαγραφή Πελάτη', 'clients', 'Δυνατότητα διαγραφής πελάτη'),
('sessions.view', 'Προβολή Συνεδριών', 'sessions', 'Δυνατότητα προβολής συνεδριών υποστήριξης'),
('sessions.create', 'Δημιουργία Συνεδρίας', 'sessions', 'Δυνατότητα δημιουργίας νέας συνεδρίας'),
('sessions.edit', 'Επεξεργασία Συνεδρίας', 'sessions', 'Δυνατότητα επεξεργασίας συνεδρίας'),
('sessions.delete', 'Διαγραφή Συνεδρίας', 'sessions', 'Δυνατότητα διαγραφής συνεδρίας'),
('payments.view', 'Προβολή Πληρωμών', 'payments', 'Δυνατότητα προβολής πληρωμών'),
('payments.create', 'Δημιουργία Πληρωμής', 'payments', 'Δυνατότητα δημιουργίας νέας πληρωμής'),
('payments.edit', 'Επεξεργασία Πληρωμής', 'payments', 'Δυνατότητα επεξεργασίας πληρωμής'),
('payments.delete', 'Διαγραφή Πληρωμής', 'payments', 'Δυνατότητα διαγραφής πληρωμής'),
('settings.view', 'Προβολή Ρυθμίσεων', 'settings', 'Δυνατότητα προβολής ρυθμίσεων'),
('settings.edit', 'Επεξεργασία Ρυθμίσεων', 'settings', 'Δυνατότητα επεξεργασίας ρυθμίσεων'),
('users.manage', 'Διαχείριση Χρηστών', 'users', 'Δυνατότητα διαχείρισης χρηστών και δικαιωμάτων');

-- Give admin all permissions
INSERT IGNORE INTO group_permissions (group_id, permission_id)
SELECT 1, id FROM permissions;

-- Insert default PDF templates
INSERT IGNORE INTO pdf_templates (template_type, template_name) VALUES 
    ('family', 'Βεβαίωση Οικογένειας'),
    ('payment', 'Απόδειξη Πληρωμής'),
    ('subscription', 'Βεβαίωση Συνδρομής');

-- Insert default support packages
INSERT IGNORE INTO support_packages (name, package_type, description, price, duration_months, prepaid_hours, is_active) VALUES
('Ωριαία Χρέωση', 'hourly', 'Χρέωση ανά ώρα υποστήριξης', 50.00, NULL, NULL, 1),
('Μηνιαία Συνδρομή', 'monthly', 'Μηνιαία συνδρομή υποστήριξης', 200.00, 1, 10.00, 1),
('Ετήσια Συνδρομή', 'yearly', 'Ετήσια συνδρομή υποστήριξης', 2000.00, 12, 120.00, 1);


-- ============================================================================
-- Schema Version Information
-- ============================================================================
-- Version: 3.2 - Support CRM (Fixed & Complete)
-- Date: January 28, 2026
-- Description: Complete Support CRM schema with all tables and proper structure
-- 
-- Features:
--   - Complete client management (families table)
--   - Support session tracking (sessions & support_sessions tables)
--   - User authentication & authorization system
--   - Payment & subscription management
--   - Support packages with prepaid hours
--   - PDF template system
--   - Audit logging
--   - License management
--   - All necessary indexes and foreign keys
-- 
-- Ready for:
--   - Fresh database installation via configurator
--   - Data migration from existing systems
--   - Full Support CRM functionality
-- ============================================================================