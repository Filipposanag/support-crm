-- Migration 023: Fix NULL emails in families table
-- Date: 2025-11-25
-- Description: Convert NULL emails to empty strings to prevent NoneType errors

-- Update NULL emails to empty string
UPDATE families 
SET email = '' 
WHERE email IS NULL;

-- Also fix NULL phone numbers while we're at it
UPDATE families 
SET phone = '' 
WHERE phone IS NULL;

-- Fix NULL first names
UPDATE families 
SET first_name = '' 
WHERE first_name IS NULL;

-- Fix NULL last names  
UPDATE families 
SET last_name = '' 
WHERE last_name IS NULL;

-- Fix NULL addresses
UPDATE families 
SET address = '' 
WHERE address IS NULL;

-- Fix NULL city
UPDATE families 
SET city = '' 
WHERE city IS NULL;

-- Fix NULL postal code
UPDATE families 
SET postal_code = '' 
WHERE postal_code IS NULL;

-- Fix NULL notes
UPDATE families 
SET notes = '' 
WHERE notes IS NULL;

-- Log the fix
SELECT 'Migration 023: Fixed NULL values in families table' as status;
