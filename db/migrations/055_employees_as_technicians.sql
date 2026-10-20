-- Migration 055: Move the 5 employee accounts to the Τεχνικοί role (group_id=2)
-- Reverses migration 049. The only administrator is the system 'admin' account.
-- Two-role model: admin = owner only; employees = technicians.

UPDATE users SET group_id = 2
 WHERE username IN ('gpapadopoulos','mioannou','ndimitriou','evasileiou','kantoniou');
