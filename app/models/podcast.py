from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship, composite
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
import json
from app.db.database import Base
import sqlalchemy


class Podcast(Base):
    __tablename__ = "podcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    cover_image = Column(String(255))
    
    # Creator relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator = relationship("User", back_populates="podcasts")
    
    # Tags stored as JSON array
    _tags = Column('tags', JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    episodes = relationship("Episode", back_populates="podcast", cascade="all, delete-orphan")
    likes = relationship("PodcastLike", back_populates="podcast", cascade="all, delete-orphan")
    comments = relationship("PodcastComment", back_populates="podcast", cascade="all, delete-orphan")
    
    # Category relationship - many-to-many
    categories = relationship(
        "Category",
        secondary="podcast_categories",
        back_populates="podcasts"
    )
    
    @hybrid_property
    def tags(self):
        if self._tags is None:
            return None
        if isinstance(self._tags, list):
            return self._tags
        try:
            return json.loads(self._tags)
        except (TypeError, json.JSONDecodeError):
            return self._tags
    
    @tags.setter
    def tags(self, value):
        if value is None:
            self._tags = None
        elif isinstance(value, list):
            self._tags = json.dumps(value)
        else:
            self._tags = value


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    audio_url = Column(String(255), nullable=False)
    duration = Column(Float, default=0)  # Duration in seconds
    
    # Cover image can be inherited from podcast if not set
    cover_image = Column(String(255))
    
    # Podcast relationship
    podcast_id = Column(Integer, ForeignKey("podcasts.id"), nullable=False)
    podcast = relationship("Podcast", back_populates="episodes")
    
    # Stream relationship
    streams = relationship("Stream", back_populates="episode")
    
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PodcastLike(Base):
    __tablename__ = "podcast_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User who liked the podcast
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="podcast_likes")
    
    # Podcast that was liked
    podcast_id = Column(Integer, ForeignKey("podcasts.id"), nullable=False)
    podcast = relationship("Podcast", back_populates="likes")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Add unique constraint to prevent duplicate likes
    __table_args__ = (
        sqlalchemy.UniqueConstraint('user_id', 'podcast_id', name='unique_user_podcast_like'),
    )


class PodcastComment(Base):
    __tablename__ = "podcast_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Comment content
    content = Column(Text, nullable=False)
    
    # User who made the comment
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="podcast_comments")
    
    # Podcast being commented on
    podcast_id = Column(Integer, ForeignKey("podcasts.id"), nullable=False)
    podcast = relationship("Podcast", back_populates="comments")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# StreamCount class removed - using Stream from stream.py instead 