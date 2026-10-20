-- Migration 049: make the 5 employee users administrators (group_id=1)
-- Date: 2026-09-08
-- Ensures they are admins even if 048 already inserted them as group 2.

UPDATE users SET group_id = 1
 WHERE username IN ('gpapadopoulos','mioannou','ndimitriou','evasileiou','kantoniou');
