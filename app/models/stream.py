from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import sqlalchemy

from app.db.database import Base

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    episode_id = Column(Integer, ForeignKey("episodes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    chunks_streamed = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    last_position = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    episode = relationship("Episode", back_populates="streams")
    user = relationship("User", back_populates="streams")
    
    # Add unique constraint to prevent duplicate stream counts per session
    __table_args__ = (
        sqlalchemy.UniqueConstraint('user_id', 'episode_id', 'created_at', name='unique_user_episode_stream'),
    ) 