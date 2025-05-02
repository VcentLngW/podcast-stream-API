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

# Define migration SQL for podcasts table
podcasts_sql = """
CREATE TABLE IF NOT EXISTS podcasts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    cover_image VARCHAR(255),
    user_id INT NOT NULL,
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# Define migration SQL for episodes table
episodes_sql = """
CREATE TABLE IF NOT EXISTS episodes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    audio_url VARCHAR(255) NOT NULL,
    duration FLOAT DEFAULT 0,
    cover_image VARCHAR(255),
    podcast_id INT NOT NULL,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);
"""

# Define migration SQL for podcast likes
likes_sql = """
CREATE TABLE IF NOT EXISTS podcast_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    podcast_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id),
    UNIQUE KEY unique_user_podcast_like (user_id, podcast_id)
);
"""

# Define migration SQL for podcast comments
comments_sql = """
CREATE TABLE IF NOT EXISTS podcast_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    user_id INT NOT NULL,
    podcast_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (podcast_id) REFERENCES podcasts(id)
);
"""

# Update tags column to JSON if it exists as VARCHAR
update_tags_sql = """
ALTER TABLE podcasts MODIFY COLUMN tags JSON;
"""

try:
    # Execute the migration SQL
    with engine.connect() as connection:
        # Create podcasts table
        connection.execute(text(podcasts_sql))
        print("Podcasts table created or already exists")
        
        # Create episodes table
        connection.execute(text(episodes_sql))
        print("Episodes table created or already exists")
        
        # Try to update tags column if needed
        try:
            connection.execute(text(update_tags_sql))
            print("Tags column updated to JSON type")
        except Exception as e:
            print(f"Note: {str(e)}")
        
        # Create likes table
        connection.execute(text(likes_sql))
        print("Podcast likes table created or already exists")
        
        # Create comments table
        connection.execute(text(comments_sql))
        print("Podcast comments table created or already exists")
            
    print("Podcast database migration completed successfully")
except Exception as e:
    print(f"Error during migration: {str(e)}") 