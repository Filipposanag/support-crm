-- Migration: Add Email and Notification Settings
-- Date: 2025-11-18
-- Description: Adds SMTP, subscription notification, and email receipt settings to app_settings table

-- Add SMTP Server settings
ALTER TABLE app_settings
ADD COLUMN smtp_host VARCHAR(255) DEFAULT '' COMMENT 'SMTP server hostname',
ADD COLUMN smtp_port INT DEFAULT 587 COMMENT 'SMTP server port',
ADD COLUMN smtp_use_tls TINYINT(1) DEFAULT 1 COMMENT 'Use TLS for SMTP connection',
ADD COLUMN smtp_username VARCHAR(255) DEFAULT '' COMMENT 'SMTP authentication username',
ADD COLUMN smtp_password VARCHAR(255) DEFAULT '' COMMENT 'SMTP authentication password',
ADD COLUMN smtp_from_email VARCHAR(255) DEFAULT '' COMMENT 'From email address',
ADD COLUMN smtp_from_name VARCHAR(255) DEFAULT '' COMMENT 'From name';

-- Add Subscription Notification settings
ALTER TABLE app_settings
ADD COLUMN days_before_expiration INT DEFAULT 30 COMMENT 'Days before expiration to highlight',
ADD COLUMN highlight_enabled TINYINT(1) DEFAULT 1 COMMENT 'Enable subscription expiration highlighting',
ADD COLUMN color_expiring VARCHAR(20) DEFAULT '#FFA500' COMMENT 'Color for expiring subscriptions',
ADD COLUMN color_expired VARCHAR(20) DEFAULT '#FF0000' COMMENT 'Color for expired subscriptions';

-- Add Email Receipt settings
ALTER TABLE app_settings
ADD COLUMN email_receipt_subject VARCHAR(255) DEFAULT 'Απόδειξη Πληρωμής' COMMENT 'Default email receipt subject',
ADD COLUMN email_receipt_body TEXT COMMENT 'Default email receipt body template';

-- Update existing row with default values ONLY if columns are NULL
-- This prevents overwriting user-configured settings on subsequent runs
UPDATE app_settings 
SET 
    smtp_host = COALESCE(smtp_host, ''),
    smtp_port = COALESCE(smtp_port, 587),
    smtp_use_tls = COALESCE(smtp_use_tls, 1),
    smtp_username = COALESCE(smtp_username, ''),
    smtp_password = COALESCE(smtp_password, ''),
    smtp_from_email = COALESCE(smtp_from_email, ''),
    smtp_from_name = COALESCE(smtp_from_name, ''),
    days_before_expiration = COALESCE(days_before_expiration, 30),
    highlight_enabled = COALESCE(highlight_enabled, 1),
    color_expiring = COALESCE(color_expiring, '#FFA500'),
    color_expired = COALESCE(color_expired, '#FF0000'),
    email_receipt_subject = COALESCE(email_receipt_subject, 'Απόδειξη Πληρωμής'),
    email_receipt_body = COALESCE(email_receipt_body, 'Σας αποστέλλουμε την απόδειξη πληρωμής σας.')
WHERE id = 1;
