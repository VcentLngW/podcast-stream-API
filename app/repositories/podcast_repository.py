from sqlalchemy.orm import Session
from typing import List, Optional
import json
from sqlalchemy.exc import IntegrityError

from app.models.podcast import Podcast, Episode, PodcastLike, PodcastComment
from app.models.category import Category
from app.schemas.podcast import PodcastCreate, PodcastUpdate, EpisodeCreate, EpisodeUpdate, CommentCreate, CommentUpdate


class PodcastRepository:
    def create_podcast(self, db: Session, podcast: PodcastCreate, user_id: int) -> Podcast:
        # No need to convert tags - the model setter will handle this
        db_podcast = Podcast(
            title=podcast.title,
            description=podcast.description,
            cover_image=podcast.cover_image,
            tags=podcast.tags,
            user_id=user_id
        )
        
        # Add categories if specified
        if podcast.category_ids:
            for cat_id in podcast.category_ids:
                category = db.query(Category).filter(Category.id == cat_id).first()
                if category:
                    db_podcast.categories.append(category)
        
        db.add(db_podcast)
        db.commit()
        db.refresh(db_podcast)
        return db_podcast
    
    def get_podcasts(self, db: Session, skip: int = 0, limit: int = 100) -> List[Podcast]:
        return db.query(Podcast).offset(skip).limit(limit).all()
    
    def get_podcasts_by_category(self, db: Session, category_id: int, skip: int = 0, limit: int = 100) -> List[Podcast]:
        return db.query(Podcast).join(Podcast.categories).filter(Category.id == category_id).offset(skip).limit(limit).all()
    
    def get_user_podcasts(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Podcast]:
        return db.query(Podcast).filter(Podcast.user_id == user_id).offset(skip).limit(limit).all()
    
    def get_podcast(self, db: Session, podcast_id: int) -> Optional[Podcast]:
        return db.query(Podcast).filter(Podcast.id == podcast_id).first()
    
    def update_podcast(self, db: Session, podcast_id: int, podcast_data: PodcastUpdate) -> Optional[Podcast]:
        db_podcast = db.query(Podcast).filter(Podcast.id == podcast_id).first()
        if db_podcast:
            update_data = podcast_data.dict(exclude_unset=True)
            
            # Handle category updates
            if 'category_ids' in update_data:
                category_ids = update_data.pop('category_ids')
                
                # Clear existing categories
                db_podcast.categories = []
                
                # Add new categories
                if category_ids:
                    for cat_id in category_ids:
                        category = db.query(Category).filter(Category.id == cat_id).first()
                        if category:
                            db_podcast.categories.append(category)
            
            # Update remaining fields
            for key, value in update_data.items():
                setattr(db_podcast, key, value)
                
            db.commit()
            db.refresh(db_podcast)
        return db_podcast
    
    def delete_podcast(self, db: Session, podcast_id: int) -> bool:
        db_podcast = db.query(Podcast).filter(Podcast.id == podcast_id).first()
        if db_podcast:
            db.delete(db_podcast)
            db.commit()
            return True
        return False
    
    # Episode operations
    def create_episode(self, db: Session, episode: EpisodeCreate, podcast_id: int) -> Episode:
        db_episode = Episode(
            title=episode.title,
            description=episode.description,
            audio_url=episode.audio_url,
            duration=episode.duration,
            cover_image=episode.cover_image,
            podcast_id=podcast_id
        )
        db.add(db_episode)
        db.commit()
        db.refresh(db_episode)
        return db_episode
    
    def get_podcast_episodes(self, db: Session, podcast_id: int, skip: int = 0, limit: int = 100) -> List[Episode]:
        return db.query(Episode).filter(Episode.podcast_id == podcast_id).offset(skip).limit(limit).all()
    
    def get_episode(self, db: Session, episode_id: int) -> Optional[Episode]:
        return db.query(Episode).filter(Episode.id == episode_id).first()
    
    def update_episode(self, db: Session, episode_id: int, episode_data: EpisodeUpdate) -> Optional[Episode]:
        db_episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if db_episode:
            update_data = episode_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_episode, key, value)
            db.commit()
            db.refresh(db_episode)
        return db_episode
    
    def delete_episode(self, db: Session, episode_id: int) -> bool:
        db_episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if db_episode:
            db.delete(db_episode)
            db.commit()
            return True
        return False
    
    # Like-related methods
    def like_podcast(self, db: Session, podcast_id: int, user_id: int) -> bool:
        """Add a like to a podcast. Returns True if the like was added, False if it already existed."""
        try:
            db_like = PodcastLike(
                podcast_id=podcast_id,
                user_id=user_id
            )
            db.add(db_like)
            db.commit()
            return True
        except IntegrityError:
            db.rollback()
            return False  # User already liked this podcast
    
    def unlike_podcast(self, db: Session, podcast_id: int, user_id: int) -> bool:
        """Remove a like from a podcast. Returns True if the like was removed, False if it didn't exist."""
        db_like = db.query(PodcastLike).filter(
            PodcastLike.podcast_id == podcast_id,
            PodcastLike.user_id == user_id
        ).first()
        
        if db_like:
            db.delete(db_like)
            db.commit()
            return True
        return False
    
    def get_podcast_likes_count(self, db: Session, podcast_id: int) -> int:
        """Get the number of likes for a podcast."""
        return db.query(PodcastLike).filter(PodcastLike.podcast_id == podcast_id).count()
    
    def user_has_liked_podcast(self, db: Session, podcast_id: int, user_id: int) -> bool:
        """Check if a user has liked a podcast."""
        return db.query(PodcastLike).filter(
            PodcastLike.podcast_id == podcast_id,
            PodcastLike.user_id == user_id
        ).first() is not None
    
    # Comment-related methods
    def create_comment(self, db: Session, podcast_id: int, user_id: int, comment_data: CommentCreate) -> PodcastComment:
        """Create a new comment on a podcast."""
        db_comment = PodcastComment(
            content=comment_data.content,
            podcast_id=podcast_id,
            user_id=user_id
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment
    
    def get_podcast_comments(self, db: Session, podcast_id: int, skip: int = 0, limit: int = 100) -> List[PodcastComment]:
        """Get all comments for a podcast."""
        return db.query(PodcastComment).filter(
            PodcastComment.podcast_id == podcast_id
        ).order_by(PodcastComment.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_comment(self, db: Session, comment_id: int) -> Optional[PodcastComment]:
        """Get a specific comment by ID."""
        return db.query(PodcastComment).filter(PodcastComment.id == comment_id).first()
    
    def update_comment(self, db: Session, comment_id: int, user_id: int, comment_data: CommentUpdate) -> Optional[PodcastComment]:
        """Update a comment. Returns None if the comment doesn't exist or doesn't belong to the user."""
        db_comment = db.query(PodcastComment).filter(
            PodcastComment.id == comment_id,
            PodcastComment.user_id == user_id
        ).first()
        
        if db_comment:
            db_comment.content = comment_data.content
            db.commit()
            db.refresh(db_comment)
            return db_comment
        return None
    
    def delete_comment(self, db: Session, comment_id: int, user_id: int) -> bool:
        """Delete a comment. Returns True if successful, False otherwise."""
        db_comment = db.query(PodcastComment).filter(
            PodcastComment.id == comment_id,
            PodcastComment.user_id == user_id
        ).first()
        
        if db_comment:
            db.delete(db_comment)
            db.commit()
            return True
        return False 