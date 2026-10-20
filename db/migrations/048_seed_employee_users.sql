-- Migration 048: Five employee users (admin group (Διαχειριστές), group_id=1)
-- Date: 2026-09-08
-- Each login is recorded in the audit log (changed_by = username).
-- Passwords (plain, for handover): giorgos123 / maria123 / nikos123 / eleni123 / kostas123

INSERT IGNORE INTO users (username, password_hash, email, first_name, last_name, group_id, is_active, is_system) VALUES
('gpapadopoulos', '$2b$12$HJKv7TFUDVcUpXvQ2tGoVeqHZN7BAgTw922V.BYA7dp.wIp8Zjgcy', 'gpapadopoulos@example.gr', 'Γεώργιος', 'Παπαδόπουλος', 1, 1, 0),
('mioannou',      '$2b$12$XHk2L1hy20HEeWcFJnBg1eBPtbgcMq5pwUYkZIpSi8Tpf.zy7EfAm', 'mioannou@example.gr', 'Μαρία', 'Ιωάννου', 1, 1, 0),
('ndimitriou',    '$2b$12$AmuBo4LeX4avzxBSNjCpJeB3zCsdHA/2ZKgxCo71Bu.S5p1BOroxO', 'ndimitriou@example.gr', 'Νίκος', 'Δημητρίου', 1, 1, 0),
('evasileiou',    '$2b$12$4oxf99lpDRVX4Xj.QF9wCOzeSQapxU4pYGN5sDqvQvq32J9.gsXZa', 'evasileiou@example.gr', 'Ελένη', 'Βασιλείου', 1, 1, 0),
('kantoniou',     '$2b$12$6B0rE819rS2TmjTAE3ZFgOGqY0w4qNyTbnmY82sKRA25GOAHqpfy2', 'kantoniou@example.gr', 'Κώστας', 'Αντωνίου', 1, 1, 0);
