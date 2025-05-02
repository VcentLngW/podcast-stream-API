import sys
import os
from pathlib import Path
import logging

# Add the parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
sys.path.append(parent_dir)

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define categories
CATEGORIES = [
    {"name": "Love", "color": "#e91e63", "icon": "Heart"},
    {"name": "Scary", "color": "#9c27b0", "icon": "Ghost"},
    {"name": "Inspirational", "color": "#2196f3", "icon": "Lightbulb"},
    {"name": "Adventure", "color": "#ff9800", "icon": "Mountain"},
    {"name": "Music", "color": "#4caf50", "icon": "Music"},
    {"name": "Education", "color": "#3f51b5", "icon": "BookOpen"},
    {"name": "Interview", "color": "#795548", "icon": "Mic"},
    {"name": "Trending", "color": "#f44336", "icon": "TrendingUp"}
]

def seed_categories():
    db = SessionLocal()
    try:
        # Check if categories already exist
        existing_categories = db.query(Category).all()
        if existing_categories:
            logger.info(f"Found {len(existing_categories)} existing categories.")
            logger.info("Skipping category seeding.")
            return
        
        # Create categories
        for category_data in CATEGORIES:
            CategoryRepository.create_category(
                db,
                name=category_data["name"],
                color=category_data["color"],
                icon=category_data["icon"]
            )
            logger.info(f"Created category: {category_data['name']}")
        
        logger.info(f"Successfully seeded {len(CATEGORIES)} categories.")
    except Exception as e:
        logger.error(f"Error seeding categories: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting category seeding...")
    seed_categories()
    logger.info("Category seeding completed.") 
 