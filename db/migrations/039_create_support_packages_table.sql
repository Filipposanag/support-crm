-- Migration 039: Create support_packages table
-- Date: 2026-01-24
-- Description: Create table for managing support packages with pricing

-- Create support_packages table
CREATE TABLE IF NOT EXISTS support_packages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL COMMENT 'Package name (e.g., "Βασικό Πακέτο")',
    package_type ENUM('hourly', 'monthly', 'yearly', 'custom') NOT NULL COMMENT 'Package type',
    description TEXT COMMENT 'Package description',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Package price in EUR',
    duration_months INT DEFAULT NULL COMMENT 'Duration in months (for subscription packages)',
    features TEXT COMMENT 'Package features (JSON or text)',
    is_active TINYINT(1) DEFAULT 1 COMMENT 'Active status',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_package_type (package_type),
    INDEX idx_is_active (is_active),
    UNIQUE KEY uk_package_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Support packages with pricing and features';

-- Insert default packages
INSERT INTO support_packages (name, package_type, description, price, duration_months, is_active) VALUES
('Ωριαία Χρέωση', 'hourly', 'Χρέωση ανά ώρα υποστήριξης', 50.00, NULL, 1),
('Μηνιαία Συνδρομή', 'monthly', 'Μηνιαία συνδρομή υποστήριξης', 200.00, 1, 1),
('Ετήσια Συνδρομή', 'yearly', 'Ετήσια συνδρομή υποστήριξης', 2000.00, 12, 1)
ON DUPLICATE KEY UPDATE updated_at = NOW();
