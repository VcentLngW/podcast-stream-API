from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Body
from sqlalchemy.orm import Session
import os
import uuid
import json
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.schemas.podcast import (
    PodcastCreate, 
    PodcastResponse, 
    PodcastDetailResponse, 
    PodcastUpdate,
    EpisodeCreate,
    EpisodeResponse,
    EpisodeUpdate,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    LikeResponse
)
from app.repositories.podcast_repository import PodcastRepository

router = APIRouter(tags=["podcasts"])
podcast_repository = PodcastRepository()

# Directory for storing uploaded files
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def check_creator_access(user: User):
    if not (user.role == UserRole.CREATOR or user.is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creator access required"
        )

# Helper function for file upload
def save_upload_file(upload_file: UploadFile) -> str:
    # Create unique filename
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Ensure directory exists
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save the file
    try:
        contents = upload_file.file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    finally:
        upload_file.file.close()
    
    return f"/uploads/{unique_filename}"  # Return relative path for storage

# Podcast routes
@router.post("/podcasts/", response_model=PodcastResponse, status_code=status.HTTP_201_CREATED, 
             summary="Create a new podcast",
             description="Create a new podcast with title, description, optional cover image, tags, and up to 3 categories")
async def create_podcast(
    title: str = Form(..., description="Podcast title"),
    description: str = Form(..., description="Podcast description"),
    tags: Optional[str] = Form(None, description="Comma-separated list or JSON array of tags"),
    category_ids: Optional[str] = Form(None, description="Comma-separated list or JSON array of category IDs (max 3)"),
    cover_image: Optional[UploadFile] = File(None, description="Podcast cover image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    cover_image_path = None
    if cover_image:
        cover_image_path = save_upload_file(cover_image)
    
    # Convert tags string to list if present
    tags_list = None
    if tags:
        try:
            # Try to parse as JSON first
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    # Convert category_ids string to list if present
    category_ids_list = None
    if category_ids:
        try:
            # Try to parse as JSON first
            category_ids_list = json.loads(category_ids)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            category_ids_list = [int(cid.strip()) for cid in category_ids.split(',') if cid.strip()]
    
    podcast_data = PodcastCreate(
        title=title,
        description=description,
        cover_image=cover_image_path,
        tags=tags_list,
        category_ids=category_ids_list
    )
    
    return podcast_repository.create_podcast(db, podcast_data, current_user.id)

@router.get("/podcasts/", response_model=List[PodcastResponse])
async def get_podcasts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        return podcast_repository.get_podcasts(db, skip=skip, limit=limit)
    except Exception as e:
        print(f"Error fetching podcasts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/podcasts/me", response_model=List[PodcastResponse])
async def get_my_podcasts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    try:
        return podcast_repository.get_user_podcasts(db, user_id=current_user.id, skip=skip, limit=limit)
    except Exception as e:
        print(f"Error fetching user podcasts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/podcasts/{podcast_id}", response_model=PodcastDetailResponse)
async def get_podcast(
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Enrich response with likes count and comments
    podcast_detail = PodcastDetailResponse.from_orm(podcast)
    podcast_detail.likes_count = podcast_repository.get_podcast_likes_count(db, podcast_id)
    
    # Get comments for the podcast
    comments = podcast_repository.get_podcast_comments(db, podcast_id)
    podcast_detail.comments = comments
    
    # Check if the current user has liked the podcast
    if current_user:
        podcast_detail.user_has_liked = podcast_repository.user_has_liked_podcast(
            db, podcast_id, current_user.id
        )
    
    return podcast_detail

@router.put("/podcasts/{podcast_id}", response_model=PodcastResponse, 
            summary="Update a podcast",
            description="Update a podcast's title, description, cover image, tags, and categories")
async def update_podcast(
    podcast_id: int,
    title: Optional[str] = Form(None, description="Podcast title"),
    description: Optional[str] = Form(None, description="Podcast description"),
    tags: Optional[str] = Form(None, description="Comma-separated list or JSON array of tags"),
    category_ids: Optional[str] = Form(None, description="Comma-separated list or JSON array of category IDs (max 3)"),
    cover_image: Optional[UploadFile] = File(None, description="Podcast cover image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    # Check if podcast exists and belongs to the user
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    if podcast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this podcast"
        )
    
    # Prepare update data
    update_data = PodcastUpdate()
    
    if title is not None:
        update_data.title = title
    if description is not None:
        update_data.description = description
    
    # Convert tags string to list if present
    if tags is not None:
        try:
            # Try to parse as JSON first
            tags_list = json.loads(tags)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        update_data.tags = tags_list
    
    # Convert category_ids string to list if present
    if category_ids is not None:
        try:
            # Try to parse as JSON first
            category_ids_list = json.loads(category_ids)
        except json.JSONDecodeError:
            # If not valid JSON, treat as comma-separated string
            category_ids_list = [int(cid.strip()) for cid in category_ids.split(',') if cid.strip()]
        update_data.category_ids = category_ids_list
    
    # Handle cover image upload if provided
    if cover_image:
        cover_image_path = save_upload_file(cover_image)
        update_data.cover_image = cover_image_path
    
    return podcast_repository.update_podcast(db, podcast_id, update_data)

@router.delete("/podcasts/{podcast_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_podcast(
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    # Check if podcast exists and belongs to the user
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    if podcast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this podcast"
        )
    
    # Delete the podcast
    podcast_repository.delete_podcast(db, podcast_id)
    return None

# Episode routes
@router.post("/podcasts/{podcast_id}/episodes/", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a podcast episode",
             description="Create a new episode for a podcast with title, description, audio file, and optional cover image")
async def create_episode(
    podcast_id: int,
    title: str = Form(..., description="Episode title"),
    description: str = Form(..., description="Episode description"),
    audio_file: UploadFile = File(..., description="Audio file for the episode"),
    cover_image: Optional[UploadFile] = File(None, description="Optional cover image for the episode"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    # Check if podcast exists and belongs to the user
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    if podcast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add episodes to this podcast"
        )
    
    # Save audio file
    audio_url = save_upload_file(audio_file)
    
    # Save cover image if provided, otherwise use podcast cover
    cover_image_path = podcast.cover_image
    if cover_image:
        cover_image_path = save_upload_file(cover_image)
    
    # Create episode
    episode_data = EpisodeCreate(
        title=title,
        description=description,
        audio_url=audio_url,
        cover_image=cover_image_path,
        duration=0  # Duration would be calculated from the audio file in a real implementation
    )
    
    return podcast_repository.create_episode(db, episode_data, podcast_id)

@router.get("/podcasts/{podcast_id}/episodes/", response_model=List[EpisodeResponse])
async def get_podcast_episodes(
    podcast_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Check if podcast exists
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    return podcast_repository.get_podcast_episodes(db, podcast_id=podcast_id, skip=skip, limit=limit)

@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: int,
    db: Session = Depends(get_db)
):
    episode = podcast_repository.get_episode(db, episode_id=episode_id)
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    return episode

@router.put("/episodes/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    # Check if episode exists
    episode = podcast_repository.get_episode(db, episode_id=episode_id)
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    # Check if the podcast belongs to the user
    podcast = podcast_repository.get_podcast(db, podcast_id=episode.podcast_id)
    if not podcast or podcast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this episode"
        )
    
    # Prepare update data
    update_data = EpisodeUpdate()
    
    if title is not None:
        update_data.title = title
    if description is not None:
        update_data.description = description
    
    # Handle file uploads if provided
    if audio_file:
        audio_url = save_upload_file(audio_file)
        update_data.audio_url = audio_url
    
    if cover_image:
        cover_image_path = save_upload_file(cover_image)
        update_data.cover_image = cover_image_path
    
    return podcast_repository.update_episode(db, episode_id, update_data)

@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user has creator access
    check_creator_access(current_user)
    
    # Check if episode exists
    episode = podcast_repository.get_episode(db, episode_id=episode_id)
    if not episode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found"
        )
    
    # Check if the podcast belongs to the user
    podcast = podcast_repository.get_podcast(db, podcast_id=episode.podcast_id)
    if not podcast or podcast.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this episode"
        )
    
    # Delete the episode
    podcast_repository.delete_episode(db, episode_id)
    return None

# Like-related endpoints
@router.post("/podcasts/{podcast_id}/like", status_code=status.HTTP_201_CREATED, response_model=dict)
async def like_podcast(
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if podcast exists
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Add like
    success = podcast_repository.like_podcast(db, podcast_id, current_user.id)
    likes_count = podcast_repository.get_podcast_likes_count(db, podcast_id)
    
    return {
        "success": success,
        "likes_count": likes_count,
        "message": "Podcast liked successfully" if success else "You already liked this podcast"
    }

@router.delete("/podcasts/{podcast_id}/like", status_code=status.HTTP_200_OK, response_model=dict)
async def unlike_podcast(
    podcast_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if podcast exists
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Remove like
    success = podcast_repository.unlike_podcast(db, podcast_id, current_user.id)
    likes_count = podcast_repository.get_podcast_likes_count(db, podcast_id)
    
    return {
        "success": success,
        "likes_count": likes_count,
        "message": "Like removed successfully" if success else "You haven't liked this podcast"
    }

# Comment-related endpoints
@router.post("/podcasts/{podcast_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    podcast_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if podcast exists
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    # Create comment
    return podcast_repository.create_comment(db, podcast_id, current_user.id, comment)

@router.get("/podcasts/{podcast_id}/comments", response_model=List[CommentResponse])
async def get_podcast_comments(
    podcast_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Check if podcast exists
    podcast = podcast_repository.get_podcast(db, podcast_id=podcast_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast not found"
        )
    
    return podcast_repository.get_podcast_comments(db, podcast_id, skip, limit)

@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    comment_update: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Update comment
    updated_comment = podcast_repository.update_comment(db, comment_id, current_user.id, comment_update)
    if not updated_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to update it"
        )
    
    return updated_comment

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is admin
    is_admin = current_user.role == UserRole.ADMIN
    
    # Get the comment to check ownership
    comment = podcast_repository.get_comment(db, comment_id)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Delete if user is comment owner or admin
    if is_admin or comment.user_id == current_user.id:
        podcast_repository.delete_comment(db, comment_id, current_user.id if not is_admin else comment.user_id)
        return None
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to delete this comment"
    ) 