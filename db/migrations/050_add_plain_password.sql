-- Migration 050: store plaintext password for admin-only visibility (demo)
-- Date: 2026-09-08
-- NOTE: plaintext passwords are insecure — kept only so the admin («admin»)
-- can view employee credentials in the Χρήστες screen (thesis/demo use).

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS plain_password VARCHAR(255) DEFAULT NULL
  COMMENT 'Plaintext password (admin-only visibility, demo)';

UPDATE users SET plain_password = 'admin123'   WHERE username = 'admin';
UPDATE users SET plain_password = 'giorgos123' WHERE username = 'gpapadopoulos';
UPDATE users SET plain_password = 'maria123'   WHERE username = 'mioannou';
UPDATE users SET plain_password = 'nikos123'   WHERE username = 'ndimitriou';
UPDATE users SET plain_password = 'eleni123'   WHERE username = 'evasileiou';
UPDATE users SET plain_password = 'kostas123'  WHERE username = 'kantoniou';
