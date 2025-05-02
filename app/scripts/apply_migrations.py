import sys
import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String, ForeignKey

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to ensure proper imports
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

def apply_migrations():
    """Apply migrations for the category tables."""
    try:
        # Use a local SQLite database for demonstration
        # Replace with your actual database connection if needed
        DATABASE_URL = "sqlite:///./test.db"
        
        logger.info(f"Connecting to database at {DATABASE_URL}")
        engine = create_engine(DATABASE_URL)
        
        # Check if tables already exist
        inspector = inspect(engine)
        metadata = MetaData()
        
        # Define tables
        categories = Table(
            "categories", 
            metadata,
            Column("id", Integer, primary_key=True, index=True),
            Column("name", String, unique=True, index=True),
            Column("description", String, nullable=True),
        )
        
        podcast_categories = Table(
            "podcast_categories",
            metadata,
            Column("id", Integer, primary_key=True, index=True),
            Column("podcast_id", Integer, ForeignKey("podcasts.id", ondelete="CASCADE")),
            Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE")),
        )
        
        # Create tables if they don't exist
        if "categories" not in inspector.get_table_names():
            logger.info("Creating categories table")
            categories.create(engine)
        else:
            logger.info("Categories table already exists")
            
        if "podcast_categories" not in inspector.get_table_names():
            logger.info("Creating podcast_categories table")
            podcast_categories.create(engine)
        else:
            logger.info("podcast_categories table already exists")
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error applying migrations: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database migrations")
    apply_migrations()
    logger.info("Migrations completed") 