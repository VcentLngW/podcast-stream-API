-- Create the podcast database if it doesn't exist
CREATE DATABASE IF NOT EXISTS podcast;

-- Create a new user with password
CREATE USER IF NOT EXISTS 'podcastuser'@'localhost' IDENTIFIED BY 'podcast123';

-- Grant privileges to the user for the podcast database
GRANT ALL PRIVILEGES ON podcast.* TO 'podcastuser'@'localhost';

-- Apply privileges
FLUSH PRIVILEGES; 