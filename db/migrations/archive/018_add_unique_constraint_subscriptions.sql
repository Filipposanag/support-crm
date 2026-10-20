-- Migration 018: Add UNIQUE constraint to subscriptions table
-- Date: 2025-11-21
-- Description: Ensures only one subscription per family per year at database level

-- Check if constraint already exists and drop it if needed (for idempotency)
-- Note: MariaDB doesn't have IF EXISTS for dropping constraints, so we use a procedure

DELIMITER $$

DROP PROCEDURE IF EXISTS add_subscription_unique_constraint$$

CREATE PROCEDURE add_subscription_unique_constraint()
BEGIN
    -- Check if the constraint already exists
    DECLARE constraint_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO constraint_exists
    FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'subscriptions'
      AND CONSTRAINT_NAME = 'uq_subscriptions_family_year'
      AND CONSTRAINT_TYPE = 'UNIQUE';
    
    -- Only add if it doesn't exist
    IF constraint_exists = 0 THEN
        ALTER TABLE subscriptions 
        ADD CONSTRAINT uq_subscriptions_family_year 
        UNIQUE KEY (family_id, year);
        
        SELECT 'UNIQUE constraint added successfully' AS status;
    ELSE
        SELECT 'UNIQUE constraint already exists' AS status;
    END IF;
END$$

DELIMITER ;

-- Execute the procedure
CALL add_subscription_unique_constraint();

-- Clean up
DROP PROCEDURE IF EXISTS add_subscription_unique_constraint;

-- Mark migration as complete
INSERT INTO schema_migrations (version, description, applied_at)
VALUES (18, 'Add UNIQUE constraint to subscriptions (family_id, year)', NOW())
ON DUPLICATE KEY UPDATE description=description;

-- Log completion
SELECT 'Migration 018 completed: UNIQUE constraint for subscriptions' as status;
