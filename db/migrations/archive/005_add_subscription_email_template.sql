-- Migration 005: Add subscription email template fields
-- Adds email_subscription_subject and email_subscription_body to app_settings

ALTER TABLE app_settings
ADD COLUMN IF NOT EXISTS email_subscription_subject VARCHAR(255) DEFAULT 'Υπενθύμιση Συνδρομής' COMMENT 'Email subject template for subscription reminders',
ADD COLUMN IF NOT EXISTS email_subscription_body TEXT DEFAULT 'Αγαπητέ/ή {family_name},\n\nΣας υπενθυμίζουμε ότι η συνδρομή σας λήγει στις {expiry_date}.\n\nΣυνολικό Ποσό: {total_amount}€\nΠληρωμένο: {paid_amount}€\nΥπόλοιπο: {remaining_amount}€\n\nΠαρακαλούμε προβείτε στην εξόφληση.\n\nΜε εκτίμηση,\n{org_name}' COMMENT 'Email body template for subscription reminders';
