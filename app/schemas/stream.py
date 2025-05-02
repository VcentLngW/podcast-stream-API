from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class StreamBase(BaseModel):
    """Base stream schema with common attributes"""
    episode_id: int
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
class StreamCreate(StreamBase):
    """Schema for creating a new stream record"""
    pass

class StreamUpdate(BaseModel):
    """Schema for updating an existing stream record"""
    stream_id: int
    chunks_streamed: Optional[int] = None
    duration_seconds: Optional[int] = None
    last_position: Optional[int] = None  # Position in seconds
    completed: Optional[bool] = None

class StreamResponse(StreamBase):
    """Schema for stream response data"""
    id: int
    chunks_streamed: int
    duration_seconds: int
    last_position: Optional[int] = None
    completed: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class EpisodeStreamStats(BaseModel):
    """Schema for episode streaming statistics"""
    episode_id: int
    total_streams: int
    completed_streams: int
    avg_duration: float
    total_duration: int
    
    model_config = ConfigDict(from_attributes=True)

class EpisodeRecommendation(BaseModel):
    """Schema for episode recommendations"""
    episode_id: int
    title: str
    description: str
    podcast_id: int
    audio_url: str
    cover_image: Optional[str] = None
    duration: float
    published_at: str
    recommendation_score: float
    recommendation_reason: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class RecentlyPlayedEpisode(BaseModel):
    """Schema for recently played episodes"""
    episode_id: int
    title: str
    description: str
    podcast_id: int
    audio_url: str
    cover_image: Optional[str] = None
    duration: float
    last_position: float
    duration_seconds: float
    completed: bool
    played_at: str
    progress_percentage: float
    
    model_config = ConfigDict(from_attributes=True) 