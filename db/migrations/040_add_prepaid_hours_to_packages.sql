-- Migration 040: Add prepaid hours to support packages
-- Date: 2026-01-24
-- Description: Add prepaid_hours field to support_packages and create client_package_hours tracking table

-- Add prepaid_hours to support_packages
ALTER TABLE support_packages
ADD COLUMN prepaid_hours DECIMAL(10,2) DEFAULT NULL COMMENT 'Prepaid hours included in package (NULL for unlimited or hourly packages)'
AFTER duration_months;

-- Create table to track prepaid hours per client
CREATE TABLE IF NOT EXISTS client_package_hours (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL COMMENT 'Client (family) ID',
    package_id INT NOT NULL COMMENT 'Support package ID',
    payment_id INT DEFAULT NULL COMMENT 'Payment ID that purchased the hours',
    total_hours DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Total prepaid hours purchased',
    used_hours DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT 'Hours used from sessions',
    remaining_hours DECIMAL(10,2) GENERATED ALWAYS AS (total_hours - used_hours) STORED COMMENT 'Remaining hours (calculated)',
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

-- Update existing packages with prepaid hours
UPDATE support_packages 
SET prepaid_hours = 10 
WHERE package_type = 'monthly' AND prepaid_hours IS NULL;

UPDATE support_packages 
SET prepaid_hours = 120 
WHERE package_type = 'yearly' AND prepaid_hours IS NULL;

-- Hourly packages don't have prepaid hours (pay per use)
UPDATE support_packages 
SET prepaid_hours = NULL 
WHERE package_type = 'hourly';
