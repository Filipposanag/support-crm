-- Migration 056: Remove legacy 'members' permissions
-- The Support CRM has no Members feature (leftover from the old families/members app).
-- No view checks members.* and they are not part of any current role baseline.
-- FK ON DELETE CASCADE cleans up group_permissions and user_permissions automatically.

DELETE FROM permissions WHERE category = 'members';
