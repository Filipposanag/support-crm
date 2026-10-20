-- Migration 058: Repair package_type for prepaid-hours packages
-- Bug: the package form lacked a 'custom' option, so editing a hours-package
-- silently saved package_type='hourly'. Any package that has prepaid hours but
-- is marked 'hourly' is really a 'custom' hours-package — restore it.
UPDATE support_packages
SET package_type = 'custom'
WHERE prepaid_hours IS NOT NULL AND prepaid_hours > 0
  AND package_type = 'hourly';
