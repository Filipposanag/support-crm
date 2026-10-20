-- Migration 008: Create Subscriptions Table
-- Creates a separate subscriptions table linked to payments
-- Date: 2025-11-19

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
    INDEX idx_subscriptions_dates (start_date, end_date),
    UNIQUE KEY uq_subscriptions_family_year (family_id, year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Subscription records linked to payments';

-- Add index for finding active subscriptions
CREATE INDEX idx_subscriptions_active ON subscriptions(status, end_date);

