-- Migration 052: editable appearance options for the receipt/invoice PDF
-- Date: 2026-09-09
-- Defaults reproduce the CURRENT look, so nothing changes until the user edits.

ALTER TABLE app_settings
  ADD COLUMN IF NOT EXISTS pdf_accent_color VARCHAR(9) DEFAULT '#1565C0'
  COMMENT 'Accent color for receipt/invoice PDF';

ALTER TABLE app_settings
  ADD COLUMN IF NOT EXISTS pdf_show_qr TINYINT(1) DEFAULT 1
  COMMENT 'Show decorative QR marking on receipt/invoice PDF';

ALTER TABLE app_settings
  ADD COLUMN IF NOT EXISTS pdf_show_session TINYINT(1) DEFAULT 1
  COMMENT 'Show linked session details on receipt/invoice PDF';

UPDATE app_settings
   SET pdf_accent_color = '#1565C0'
 WHERE pdf_accent_color IS NULL OR pdf_accent_color = '';
