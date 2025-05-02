from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Response, Query
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import os
import io
import math
import pathlib
import mimetypes
from datetime import datetime, timedelta
from sqlalchemy.sql import func, desc

from app.db.database import get_db
from app.core.config import settings
from app.repositories.stream_repository import StreamRepository
from app.repositories.podcast_repository import PodcastRepository
from app.repositories.user_repository import UserRepository
from app.api.deps import get_current_user
from app.models.user import User
from app.models.podcast import Episode
from app.models.stream import Stream
from app.schemas.stream import StreamCreate, StreamUpdate, StreamResponse, EpisodeRecommendation, RecentlyPlayedEpisode

router = APIRouter(
    prefix="/stream",
    tags=["stream"],
    responses={404: {"description": "Not found"}},
)

# Use a smaller chunk size for streaming
CHUNK_SIZE = 512 * 1024  # 512KB chunks

# Define optional user dependency
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token provided, return None if no token or invalid token"""
    # Try to get token from Swagger UI security scheme first
    token = None
    if credentials:
        token = credentials.credentials
    # Then try from Authorization header
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
            
        user = UserRepository.get_user_by_email(db, email=email)
        if user is None:
            return None
            
        return user
    except JWTError:
        return None

def get_client_info(request: Request):
    """Extract client information from request"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent")
    }

@router.get("/episodes/{episode_id}")
async def stream_episode(
    episode_id: int,
    request: Request,
    response: Response,
    range: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Stream audio file in chunks with range support"""
    # Get episode
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    # Get the project root directory - but here we need the backend directory
    backend_dir = pathlib.Path(__file__).parent.parent.parent  # Go up 3 levels from this file to reach backend
    
    # Check if audio_url is a relative path (starts with /)
    audio_url = episode.audio_url
    if audio_url.startswith('/'):
        # Remove the leading slash if present to avoid double slashes
        audio_url = audio_url[1:] if audio_url.startswith('/') else audio_url
        # Create absolute path from the backend directory
        audio_path = os.path.join(backend_dir, audio_url)
    else:
        # Use as is if it's already an absolute path
        audio_path = audio_url
    
    # Debug logging
    print(f"Original audio URL: {episode.audio_url}")
    print(f"Backend directory: {backend_dir}")
    print(f"Resolved audio path: {audio_path}")
    print(f"File exists: {os.path.isfile(audio_path)}")
    
    # Check if file exists
    if not os.path.isfile(audio_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Audio file not found at path: {audio_path}"
        )
    
    # Create or update stream record
    client_info = get_client_info(request)
    user_id = current_user.id if current_user else None
    
    # Create a new stream record if this is the first request
    if not range:
        stream_record = StreamRepository.create_stream(
            db=db,
            episode_id=episode_id,
            user_id=user_id,
            **client_info
        )
        # Store stream_id in headers to track session
        response.headers["X-Stream-ID"] = str(stream_record.id)
    
    # Get file size
    file_size = os.path.getsize(audio_path)
    
    # Parse range header
    start = 0
    end = file_size - 1
    
    if range:
        try:
            range_match = range.replace("bytes=", "").split("-")
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
            
            # Ensure start and end are within valid range
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            
            print(f"Range request: start={start}, end={end}, file_size={file_size}")
        except (ValueError, IndexError) as e:
            print(f"Error parsing range header '{range}': {e}")
            start = 0
            end = file_size - 1
    
    # Calculate content length
    content_length = end - start + 1
    
    # Determine content type
    content_type = mimetypes.guess_type(audio_path)[0]
    if not content_type:
        # Default to MP3 if extension not recognized
        if audio_path.lower().endswith(('.mp3', '.mpeg')):
            content_type = "audio/mpeg"
        elif audio_path.lower().endswith('.wav'):
            content_type = "audio/wav"
        elif audio_path.lower().endswith('.ogg'):
            content_type = "audio/ogg"
        elif audio_path.lower().endswith('.m4a'):
            content_type = "audio/mp4"
        else:
            content_type = "application/octet-stream"  # Generic binary
    
    print(f"Content type: {content_type}")
    
    # Set response headers
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": content_type,
        "Cache-Control": "public, max-age=31536000"  # Cache for a year
    }
    
    # Create a generator to stream the file in chunks
    def file_iterator():
        with open(audio_path, "rb") as f:
            f.seek(start)
            bytes_sent = 0
            while bytes_sent < content_length:
                chunk_size = min(CHUNK_SIZE, content_length - bytes_sent)
                data = f.read(chunk_size)
                if not data:
                    break
                bytes_sent += len(data)
                yield data
                
                # Debug logging for every 10 chunks
                if bytes_sent % (CHUNK_SIZE * 10) == 0:
                    print(f"Streaming progress: {bytes_sent}/{content_length} bytes ({bytes_sent/content_length:.1%})")
    
    # Return streaming response
    return StreamingResponse(
        file_iterator(),
        status_code=206 if range else 200,
        headers=headers
    )

@router.post("/track", response_model=StreamResponse)
async def track_stream(
    stream_data: StreamUpdate,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Update stream tracking data"""
    # Get stream record
    updated_stream = StreamRepository.update_stream(
        db=db,
        stream_id=stream_data.stream_id,
        chunks_streamed=stream_data.chunks_streamed,
        duration_seconds=stream_data.duration_seconds,
        last_position=stream_data.last_position,
        completed=stream_data.completed
    )
    
    return StreamResponse.from_orm(updated_stream)

@router.get("/stats/episode/{episode_id}", response_model=Dict[str, Any])
async def get_episode_stats(
    episode_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get streaming statistics for an episode"""
    if current_user.role not in ["admin", "creator"]:
        raise HTTPException(status_code=403, detail="Not authorized to view episode statistics")
    
    stats = StreamRepository.get_episode_stream_stats(db=db, episode_id=episode_id)
    return stats

@router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_episodes(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get most popular episodes based on stream count"""
    popular = StreamRepository.get_popular_episodes(db=db, limit=limit)
    return popular

@router.get("/recommendations", response_model=List[EpisodeRecommendation])
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations to return"),
    category_id: Optional[int] = Query(None, description="Filter recommendations to a specific category"),
    exclude_listened: bool = Query(True, description="Exclude episodes the user has already listened to"),
    include_reasons: bool = Query(True, description="Include human-readable reasons for recommendations"),
    db: Session = Depends(get_db)
):
    """
    Get personalized episode recommendations based on streaming history and user engagement
    
    - **limit**: Maximum number of recommendations to return
    - **category_id**: Filter recommendations to a specific category
    - **exclude_listened**: Exclude episodes the user has already listened to
    - **include_reasons**: Include human-readable reasons for recommendations
    """
    recommendations = StreamRepository.get_user_recommendations(
        db=db, 
        user_id=current_user.id, 
        limit=limit,
        category_id=category_id,
        exclude_listened=exclude_listened,
        include_reasons=include_reasons
    )
    return recommendations

@router.get("/recommendations/guest", response_model=List[EpisodeRecommendation])
async def get_guest_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations to return"),
    category_id: Optional[int] = Query(None, description="Filter recommendations to a specific category"),
    db: Session = Depends(get_db)
):
    """
    Get episode recommendations for guest users (no login required)
    
    Returns trending episodes based on recent popularity and engagement metrics
    
    - **limit**: Maximum number of recommendations to return
    - **category_id**: Filter recommendations to a specific category
    """
    # For guest users, we'll use a different approach - just popular and recent content
    
    # Get base query conditions
    base_conditions = []
    if category_id is not None:
        # Import the join table model for category filtering
        from app.models.podcast import Podcast
        from sqlalchemy import Table, Column, ForeignKey, MetaData
        from app.db.database import Base
        
        # Define the association table for podcast categories
        podcast_categories = Table(
            'podcast_categories',
            Base.metadata,
            Column('podcast_id', ForeignKey('podcasts.id'), primary_key=True),
            Column('category_id', ForeignKey('categories.id'), primary_key=True)
        )
        
        base_conditions.append(
            Episode.podcast_id.in_(
                db.query(podcast_categories.c.podcast_id).filter(
                    podcast_categories.c.category_id == category_id
                )
            )
        )
    
    # Import SQLAlchemy functions for counting and ordering
    from sqlalchemy.sql import func, desc
    
    # Get popular episodes from the last month
    one_month_ago = datetime.now() - timedelta(days=30)
    popular_episodes = db.query(
        Episode,
        func.count(Stream.id).label('stream_count')
    ).join(
        Stream, Stream.episode_id == Episode.id
    ).filter(
        Episode.published_at >= one_month_ago,
        *base_conditions
    ).group_by(
        Episode.id
    ).order_by(
        desc('stream_count')
    ).limit(limit).all()
    
    # Format the results
    recommendations = []
    for episode, stream_count in popular_episodes:
        recommendations.append({
            "episode_id": episode.id,
            "title": episode.title,
            "description": episode.description,
            "podcast_id": episode.podcast_id,
            "audio_url": episode.audio_url,
            "cover_image": episode.cover_image,
            "duration": episode.duration,
            "published_at": episode.published_at.isoformat(),
            "recommendation_score": float(stream_count),
            "recommendation_reason": "Trending episode"
        })
    
    return recommendations

@router.get("/recently-played", response_model=List[RecentlyPlayedEpisode])
async def get_recently_played_episodes(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recently played episodes to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back for recently played episodes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recently played episodes for the current user.
    Returns episodes with their playback progress and completion status.
    """
    recent_episodes = StreamRepository.get_recently_played_episodes(
        db=db,
        user_id=current_user.id,
        limit=limit,
        days=days
    )
    
    return recent_episodes 