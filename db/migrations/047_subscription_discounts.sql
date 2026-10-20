-- Migration 047: Subscription pricing with discount vs the 40€/hour rate
-- Date: 2026-09-08

UPDATE support_packages SET price = 100.00,
  description = 'Μηνιαία υποστήριξη: 3 ώρες/μήνα (~33€/ώρα, -17%). Προτεραιότητα εξυπηρέτησης.'
  WHERE name = 'Μηνιαία Συνδρομή';

UPDATE support_packages SET price = 1000.00,
  description = 'Ετήσια συνδρομή: 36 ώρες/έτος (~28€/ώρα, -30%). Η καλύτερη τιμή για σταθερούς πελάτες.'
  WHERE name = 'Ετήσια Συνδρομή';
