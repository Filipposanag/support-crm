-- Migration 046: Package prices with real discounts vs the 40€/hour rate
-- Date: 2026-09-08

UPDATE support_packages SET price = 180.00,
  description = '5 προπληρωμένες ώρες (36€/ώρα, -10%). Οικονομία 20€ έναντι της ωριαίας.'
  WHERE name = 'Πακέτο 5 Ωρών';

UPDATE support_packages SET price = 340.00,
  description = '10 προπληρωμένες ώρες (34€/ώρα, -15%). Οικονομία 60€.'
  WHERE name = 'Πακέτο 10 Ωρών';

UPDATE support_packages SET price = 640.00,
  description = '20 προπληρωμένες ώρες (32€/ώρα, -20%). Οικονομία 160€.'
  WHERE name = 'Πακέτο 20 Ωρών';

UPDATE support_packages SET price = 1200.00,
  description = '40 προπληρωμένες ώρες (30€/ώρα, -25%). Οικονομία 400€. Για επιχειρήσεις.'
  WHERE name = 'Πακέτο 40 Ωρών';
