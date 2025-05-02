#!/usr/bin/env python
"""
Category Creation Script

This script populates the database with predefined podcast categories.
Each category includes a name, color (hex code), and an icon identifier.

Usage:
    python create_categories.py

The script will:
1. Connect to the database using settings from app/core/config.py
2. Check for existing categories to avoid duplicates
3. Add new categories that don't already exist
4. Output the results to the console

Make sure your .env file is properly configured with database credentials.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.category import Category
from app.core.config import settings

# Load environment variables
load_dotenv()

# Use database URL from settings
DATABASE_URL = f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Define categories to insert
PODCAST_CATEGORIES = [
    {"name": "Technology", "color": "#3498db", "icon": "computer"},
    {"name": "Business", "color": "#2ecc71", "icon": "business_center"},
    {"name": "Science", "color": "#9b59b6", "icon": "science"},
    {"name": "Health", "color": "#e74c3c", "icon": "healing"},
    {"name": "Education", "color": "#f39c12", "icon": "school"},
    {"name": "Entertainment", "color": "#1abc9c", "icon": "movie"},
    {"name": "Sports", "color": "#d35400", "icon": "sports_basketball"},
    {"name": "News", "color": "#7f8c8d", "icon": "newspaper"},
    {"name": "Society", "color": "#27ae60", "icon": "groups"},
    {"name": "Culture", "color": "#8e44ad", "icon": "theater_comedy"}
]

def create_categories():
    """Create podcast categories in the database."""
    # Create SQLAlchemy engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check existing categories to avoid duplicates
        existing_category_names = [c.name for c in db.query(Category).all()]
        
        # Counter for added categories
        added_count = 0
        
        for category_data in PODCAST_CATEGORIES:
            if category_data["name"] not in existing_category_names:
                # Create a new category
                category = Category(
                    name=category_data["name"],
                    color=category_data["color"],
                    icon=category_data["icon"]
                )
                
                db.add(category)
                added_count += 1
                print(f"Added category: {category_data['name']}")
            else:
                print(f"Category {category_data['name']} already exists.")
        
        db.commit()
        print(f"\nAdded {added_count} new categories to the database.")
        
        # Display summary of all categories in the database
        all_categories = db.query(Category).all()
        print(f"\nTotal categories in database: {len(all_categories)}")
        print("\nCurrent Categories:")
        print("------------------")
        for category in all_categories:
            print(f"ID: {category.id} | Name: {category.name} | Color: {category.color} | Icon: {category.icon}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Error creating categories: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting category creation process...")
    success = create_categories()
    if success:
        print("\nCategory creation process completed successfully.")
    else:
        print("\nCategory creation process failed.") 