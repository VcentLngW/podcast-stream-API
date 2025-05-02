from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User, UserRole
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.podcast import PodcastResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])


# Dependency to check if current user is admin
def is_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )
    return current_user


@router.get("/", response_model=List[CategoryResponse])
async def get_all_categories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all podcast categories."""
    categories = CategoryRepository.get_all_categories(db, skip, limit)
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific category by ID."""
    category = CategoryRepository.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)  # Only admins can create categories
):
    """Create a new podcast category."""
    # Check if category with same name already exists
    existing_category = CategoryRepository.get_category_by_name(db, category.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    new_category = CategoryRepository.create_category(
        db, 
        name=category.name, 
        color=category.color, 
        icon=category.icon
    )
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)  # Only admins can update categories
):
    """Update an existing podcast category."""
    # Check if category exists
    category = CategoryRepository.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if new name already exists (if name is being updated)
    if category_data.name and category_data.name != category.name:
        existing_category = CategoryRepository.get_category_by_name(db, category_data.name)
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
    
    updated_category = CategoryRepository.update_category(
        db, 
        category_id, 
        category_data.dict(exclude_unset=True)
    )
    return updated_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_admin)  # Only admins can delete categories
):
    """Delete a podcast category."""
    # Check if category exists
    category = CategoryRepository.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    CategoryRepository.delete_category(db, category_id)
    return None


@router.get("/{category_id}/podcasts", response_model=List[PodcastResponse],
           summary="Get podcasts by category",
           description="Retrieve all podcasts associated with a specific category")
async def get_podcasts_by_category(
    category_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all podcasts that belong to a specific category."""
    # First check if category exists
    category = CategoryRepository.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Get podcasts for this category
    podcasts = CategoryRepository.get_podcasts_by_category(db, category_id, skip, limit)
    return podcasts 