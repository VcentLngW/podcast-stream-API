import os
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", "3306"))
db_user = os.getenv("DB_USER", "podcastuser")
db_password = os.getenv("DB_PASSWORD", "podcast123")
db_name = os.getenv("DB_NAME", "podcast")

# Construct database URL
DATABASE_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Define migration SQL
migration_sql = """
ALTER TABLE users 
ADD COLUMN role ENUM('LISTENER', 'CREATOR', 'ADMIN') NOT NULL DEFAULT 'LISTENER',
ADD COLUMN is_creator BOOLEAN NOT NULL DEFAULT FALSE;
"""

# Define additional migration for name and username changes
name_migration_sql = """
ALTER TABLE users 
ADD COLUMN name VARCHAR(100),
MODIFY username VARCHAR(50) NULL;
"""

try:
    # Execute the migration SQL
    with engine.connect() as connection:
        # Check if columns already exist before adding
        result = connection.execute(text("SHOW COLUMNS FROM users LIKE 'role';"))
        role_exists = result.rowcount > 0
        
        result = connection.execute(text("SHOW COLUMNS FROM users LIKE 'is_creator';"))
        is_creator_exists = result.rowcount > 0
        
        if not role_exists and not is_creator_exists:
            connection.execute(text(migration_sql))
            print("Migration successful - Added role columns to users table")
        else:
            print("Role columns already exist, no migration needed")
        
        # Check for name column
        result = connection.execute(text("SHOW COLUMNS FROM users LIKE 'name';"))
        name_exists = result.rowcount > 0
        
        if not name_exists:
            connection.execute(text(name_migration_sql))
            print("Migration successful - Updated name and username columns")
        else:
            print("Name column already exists, no migration needed")
            
    print("Database migration completed successfully")
except Exception as e:
    print(f"Error during migration: {str(e)}") 