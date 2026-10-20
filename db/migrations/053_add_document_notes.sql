-- Migration 053: optional technician comments printed on the document
-- Date: 2026-09-09
-- Description: Adds a free-text notes field on the payment, captured at
-- document issue time (Απόδειξη / Τιμολόγιο) and printed on the PDF.
-- Kept separate from `remarks` (internal payment notes) so it can be shown
-- to the client on the receipt/invoice without exposing internal notes.

ALTER TABLE payments
  ADD COLUMN IF NOT EXISTS document_notes TEXT
  COMMENT 'Optional technician comments about the work, printed on the receipt/invoice';
