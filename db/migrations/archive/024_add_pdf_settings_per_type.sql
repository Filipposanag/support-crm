-- Migration 024: Add separate PDF settings for payments and subscriptions
-- Date: December 2025
-- Description: Adds separate title and footer fields for payment receipts and subscription certificates

-- Add payment PDF settings (using ALTER IGNORE for MariaDB compatibility)
ALTER TABLE app_settings 
ADD COLUMN pdf_payment_title VARCHAR(200) DEFAULT 'Απόδειξη Πληρωμής' COMMENT 'PDF title for payment receipts';

ALTER TABLE app_settings 
ADD COLUMN pdf_payment_footer TEXT COMMENT 'PDF footer for payment receipts';

-- Add subscription PDF settings
ALTER TABLE app_settings 
ADD COLUMN pdf_subscription_title VARCHAR(200) DEFAULT 'Βεβαίωση Συνδρομής' COMMENT 'PDF title for subscription certificates';

ALTER TABLE app_settings 
ADD COLUMN pdf_subscription_footer TEXT COMMENT 'PDF footer for subscription certificates';

-- Copy existing values as defaults
UPDATE app_settings 
SET pdf_payment_title = COALESCE(pdf_title, 'Απόδειξη Πληρωμής'),
    pdf_payment_footer = pdf_footer,
    pdf_subscription_title = COALESCE(pdf_title, 'Βεβαίωση Συνδρομής'),
    pdf_subscription_footer = pdf_footer
WHERE id = 1;
