from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

from app.schemas.category import CategoryResponse


class EpisodeBase(BaseModel):
    title: str
    description: str
    duration: float = 0


class EpisodeCreate(EpisodeBase):
    audio_url: str
    cover_image: Optional[str] = None


class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    cover_image: Optional[str] = None


class EpisodeResponse(EpisodeBase):
    id: int
    podcast_id: int
    audio_url: str
    cover_image: Optional[str] = None
    published_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PodcastBase(BaseModel):
    title: str
    description: str


class PodcastCreate(PodcastBase):
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None
    category_ids: Optional[List[int]] = Field(default=None, description="List of category IDs (max 3)")
    
    @validator('category_ids')
    def validate_category_count(cls, v):
        if v is not None and len(v) > 3:
            raise ValueError('A podcast can have a maximum of 3 categories')
        return v


class PodcastUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None
    category_ids: Optional[List[int]] = Field(default=None, description="List of category IDs (max 3)")
    
    @validator('category_ids')
    def validate_category_count(cls, v):
        if v is not None and len(v) > 3:
            raise ValueError('A podcast can have a maximum of 3 categories')
        return v


class PodcastResponse(PodcastBase):
    id: int
    user_id: int
    cover_image: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: List[CategoryResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(CommentBase):
    id: int
    user_id: int
    podcast_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LikeCreate(BaseModel):
    pass


class LikeResponse(BaseModel):
    id: int
    user_id: int
    podcast_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PodcastDetailResponse(PodcastResponse):
    episodes: List[EpisodeResponse] = []
    likes_count: int = 0
    comments: List[CommentResponse] = []
    user_has_liked: bool = False

    class Config:
        from_attributes = True 