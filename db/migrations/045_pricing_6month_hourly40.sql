-- Migration 045: Pricing — 6-month validity for hour packages + 40€ hourly rate
-- Date: 2026-09-08

-- Prepaid hour-packages (5/10/20/40 ώρες): 6-month validity
UPDATE support_packages
   SET duration_months = 6
 WHERE prepaid_hours IS NOT NULL AND prepaid_hours > 0
   AND package_type NOT IN ('monthly', 'yearly');

-- Standard hourly rate = 40€ (per started hour, block billing)
UPDATE app_settings SET default_hourly_rate = 40.00 WHERE id = 1;

-- Keep the "Ωριαία Χρέωση" catalog entry consistent at 40€
UPDATE support_packages SET price = 40.00 WHERE package_type = 'hourly';
