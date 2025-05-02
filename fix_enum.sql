-- Drop existing columns if they exist
ALTER TABLE users 
DROP COLUMN IF EXISTS role,
DROP COLUMN IF EXISTS is_creator;

-- Add columns with correct enum values
ALTER TABLE users 
ADD COLUMN role ENUM('LISTENER', 'CREATOR', 'ADMIN') NOT NULL DEFAULT 'LISTENER',
ADD COLUMN is_creator BOOLEAN NOT NULL DEFAULT FALSE; 