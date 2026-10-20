-- Migration 051: make PDF document titles editable from Settings > «Ρυθμίσεις PDF»
-- Date: 2026-09-09
-- The receipt/invoice title is now read from app_settings by receipt_service.
-- Seed the current on-document headings so the Settings fields match what is
-- printed today. Only overwrite empty or leftover generic values (never a real
-- custom title the user may have set).

UPDATE app_settings
   SET pdf_payment_title = 'ΑΠΟΔΕΙΞΗ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ'
 WHERE pdf_payment_title IS NULL
    OR pdf_payment_title = ''
    OR pdf_payment_title = 'Απόδειξη Πληρωμής';

UPDATE app_settings
   SET pdf_subscription_title = 'ΤΙΜΟΛΟΓΙΟ ΠΑΡΟΧΗΣ ΥΠΗΡΕΣΙΩΝ'
 WHERE pdf_subscription_title IS NULL
    OR pdf_subscription_title = ''
    OR pdf_subscription_title = 'Βεβαίωση Συνδρομής';
