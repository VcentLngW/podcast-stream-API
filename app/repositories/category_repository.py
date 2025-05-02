from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.podcast import Podcast


class CategoryRepository:
    @staticmethod
    def get_category_by_id(db: Session, category_id: int) -> Optional[Category]:
        return db.query(Category).filter(Category.id == category_id).first()
    
    @staticmethod
    def get_category_by_name(db: Session, name: str) -> Optional[Category]:
        return db.query(Category).filter(Category.name == name).first()
    
    @staticmethod
    def get_all_categories(db: Session, skip: int = 0, limit: int = 100) -> List[Category]:
        return db.query(Category).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_category(db: Session, name: str, color: str, icon: Optional[str] = None) -> Category:
        db_category = Category(name=name, color=color, icon=icon)
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category
    
    @staticmethod
    def update_category(db: Session, category_id: int, data: dict) -> Optional[Category]:
        db_category = CategoryRepository.get_category_by_id(db, category_id)
        if db_category:
            for key, value in data.items():
                if hasattr(db_category, key) and value is not None:
                    setattr(db_category, key, value)
            db.commit()
            db.refresh(db_category)
        return db_category
    
    @staticmethod
    def delete_category(db: Session, category_id: int) -> bool:
        db_category = CategoryRepository.get_category_by_id(db, category_id)
        if db_category:
            db.delete(db_category)
            db.commit()
            return True
        return False
        
    @staticmethod
    def get_podcasts_by_category(db: Session, category_id: int, skip: int = 0, limit: int = 100) -> List[Podcast]:
        """Get all podcasts associated with a specific category."""
        category = CategoryRepository.get_category_by_id(db, category_id)
        if not category:
            return []
            
        return category.podcasts[skip:skip+limit] 