-- Migration 027: Add email certificate settings
-- Adds fields for family certificate email template

-- Add email certificate subject
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS email_certificate_subject VARCHAR(255) DEFAULT 'Βεβαίωση Εγγραφής' 
COMMENT 'Default email certificate subject';

-- Add email certificate body
ALTER TABLE app_settings 
ADD COLUMN IF NOT EXISTS email_certificate_body TEXT 
COMMENT 'Default email certificate body template';

-- Set default value for existing rows
UPDATE app_settings 
SET email_certificate_subject = 'Βεβαίωση Εγγραφής',
    email_certificate_body = 'Αγαπητέ/ή {family_name},\n\nΣας αποστέλλουμε τη βεβαίωση εγγραφής σας στον σύλλογό μας.\n\nΑριθμός Μητρώου: {family_code}\nΑριθμός Μελών: {members_count}\n\nΜε εκτίμηση,\n{org_name}'
WHERE id = 1 AND (email_certificate_subject IS NULL OR email_certificate_subject = '');
