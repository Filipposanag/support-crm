-- Migration 007: Enforce Subscription Payment Rule
-- Ensures that subscriptions can only be created with paid receipts
-- Date: 2025-11-19

-- NOTE: Database triggers are NOT used in this implementation.
-- The validation is enforced at the application layer instead:
-- - UI Layer: payment_form.py
-- - Repository Layer: payments_repo.py, subscriptions_repo.py
-- This provides better error handling, flexibility, and avoids SQL syntax issues.

-- Add comment to payments table documenting the rule
ALTER TABLE payments 
COMMENT='Payment and subscription records. Subscriptions require paid_amount > 0 and status != UNPAID (enforced at application layer)';

-- No triggers are created by this migration.
-- Validation is handled in Python code for better control and error handling.

