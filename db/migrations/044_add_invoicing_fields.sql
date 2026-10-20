-- Migration 044: Invoicing fields (Απόδειξη / Τιμολόγιο + ΦΠΑ)
-- Date: 2026-09-08
-- Description: Adds client tax fields (ΑΦΜ/ΔΟΥ), payment document type + VAT
-- snapshot, and configurable VAT rate + invoice numbering series in settings.

-- Client tax fields (required when issuing a Τιμολόγιο to a business/professional)
ALTER TABLE families
  ADD COLUMN IF NOT EXISTS afm VARCHAR(20) DEFAULT '' COMMENT 'Client Tax ID (ΑΦΜ) - required for invoices',
  ADD COLUMN IF NOT EXISTS doy VARCHAR(100) DEFAULT '' COMMENT 'Client tax office (ΔΟΥ) - for invoices';

-- Payment: which document was issued, and the VAT rate captured at issue time
ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS document_type VARCHAR(20) DEFAULT 'receipt' COMMENT 'Issued document: receipt (Απόδειξη) or invoice (Τιμολόγιο)',
  ADD COLUMN IF NOT EXISTS vat_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT 'VAT % applied at issue time (snapshot for stable historical docs)';

-- Settings: configurable VAT rate + separate invoice numbering series (ΤΠΥ-0001)
ALTER TABLE app_settings
  ADD COLUMN IF NOT EXISTS vat_rate DECIMAL(5,2) DEFAULT 24.00 COMMENT 'Default VAT rate (%) for documents (0 = no VAT breakdown)',
  ADD COLUMN IF NOT EXISTS invoice_counter INT DEFAULT 1 COMMENT 'Next invoice number',
  ADD COLUMN IF NOT EXISTS invoice_prefix VARCHAR(20) DEFAULT 'ΤΠΥ' COMMENT 'Invoice number prefix';

-- Index for filtering by document type
ALTER TABLE payments ADD INDEX IF NOT EXISTS idx_payments_document_type (document_type);
