from sqlalchemy import column
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case, literal
from fastapi import HTTPException, status

from app.models.stream import Stream
from app.models.podcast import Episode, Podcast, PodcastLike, PodcastComment
from app.models.user import User
from app.models.category import Category


class StreamRepository:
    @staticmethod
    def create_stream(
        db: Session,
        episode_id: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Stream:
        """
        Create a new stream record when a user starts streaming an episode.
        """
        # Check if episode exists
        episode = db.query(Episode).filter(Episode.id == episode_id).first()
        if not episode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Episode not found"
            )
            
        # Create new stream record
        stream_record = Stream(
            episode_id=episode_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            chunks_streamed=0,
            duration_seconds=0,
            completed=False,
            last_position=0
        )
        
        db.add(stream_record)
        db.commit()
        db.refresh(stream_record)
        
        return stream_record
        
    @staticmethod
    def update_stream(
        db: Session,
        stream_id: int,
        chunks_streamed: int,
        duration_seconds: float,
        last_position: float,
        completed: bool = False
    ) -> Stream:
        """
        Update an existing stream record with new streaming data.
        """
        stream_record = db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream record not found"
            )
            
        # Update stream data
        stream_record.chunks_streamed = chunks_streamed
        stream_record.duration_seconds = duration_seconds
        stream_record.last_position = last_position
        stream_record.completed = completed
        
        db.commit()
        db.refresh(stream_record)
        
        return stream_record
        
    @staticmethod
    def get_user_streams(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Stream]:
        """
        Get all streams for a specific user.
        """
        return db.query(Stream).filter(
            Stream.user_id == user_id
        ).order_by(
            desc(Stream.created_at)
        ).offset(skip).limit(limit).all()
        
    @staticmethod
    def get_episode_stream_stats(
        db: Session,
        episode_id: int
    ) -> Dict[str, Any]:
        """
        Get streaming statistics for a specific episode.
        """
        # Count total streams
        total_streams = db.query(func.count(Stream.id)).filter(
            Stream.episode_id == episode_id
        ).scalar()
        
        # Count completed streams
        completed_streams = db.query(func.count(Stream.id)).filter(
            Stream.episode_id == episode_id,
            Stream.completed == True
        ).scalar()
        
        # Calculate average duration streamed
        avg_duration = db.query(func.avg(Stream.duration_seconds)).filter(
            Stream.episode_id == episode_id
        ).scalar() or 0
        
        # Calculate total duration streamed
        total_duration = db.query(func.sum(Stream.duration_seconds)).filter(
            Stream.episode_id == episode_id
        ).scalar() or 0
        
        return {
            "total_streams": total_streams,
            "completed_streams": completed_streams,
            "completion_rate": (completed_streams / total_streams) * 100 if total_streams > 0 else 0,
            "avg_duration": float(avg_duration),
            "total_duration": float(total_duration)
        }
        
    @staticmethod
    def get_popular_episodes(
        db: Session,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the most popular episodes based on stream count.
        """
        # Query for episodes with the most streams
        popular_episodes = db.query(
            Stream.episode_id,
            func.count(Stream.id).label('stream_count')
        ).group_by(
            Stream.episode_id
        ).order_by(
            desc('stream_count')
        ).limit(limit).all()
        
        result = []
        for episode_id, stream_count in popular_episodes:
            episode = db.query(Episode).filter(Episode.id == episode_id).first()
            if episode:
                result.append({
                    "episode_id": episode_id,
                    "title": episode.title,
                    "stream_count": stream_count,
                    "podcast_id": episode.podcast_id
                })
                
        return result
    
    @staticmethod
    def get_user_recommendations(
        db: Session,
        user_id: int,
        limit: int = 5,
        category_id: Optional[int] = None,
        exclude_listened: bool = True,
        include_reasons: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get episode recommendations for a user based on their streaming history,
        likes, comments, and completion rate.
        
        The recommendation algorithm considers:
        1. Content from podcasts the user has streamed with high completion rates
        2. Content with similar tags/categories as the user's favorites
        3. Popular content among users with similar interests
        4. New episodes from podcasts the user has engaged with
        5. Recommendations from diverse categories to avoid echo chambers
        
        Args:
            db: Database session
            user_id: User ID to get recommendations for
            limit: Maximum number of recommendations to return
            category_id: Optional category ID to filter recommendations by
            exclude_listened: Whether to exclude episodes the user has already listened to
            include_reasons: Whether to include human-readable reasons for recommendations
        """
        # Get episodes the user has already streamed
        streamed_episodes = db.query(Stream.episode_id).filter(
            Stream.user_id == user_id
        ).distinct().all()
        
        streamed_episode_ids = [episode_id for (episode_id,) in streamed_episodes]
        
        # --- 1. Get podcasts the user has engaged with ---
        
        # Podcasts with high completion rates
        high_completion_podcasts = db.query(
            Episode.podcast_id,
            func.avg(case((Stream.completed == True, 1), else_=0)).label('completion_rate')
        ).join(
            Stream, Stream.episode_id == Episode.id
        ).filter(
            Stream.user_id == user_id
        ).group_by(
            Episode.podcast_id
        ).having(
            func.avg(case((Stream.completed == True, 1), else_=0)) > 0.5  # 50% completion rate
        ).all()
        
        # Podcasts the user has liked
        liked_podcasts = db.query(PodcastLike.podcast_id).filter(
            PodcastLike.user_id == user_id
        ).all()
        
        # Podcasts the user has commented on
        commented_podcasts = db.query(PodcastComment.podcast_id).filter(
            PodcastComment.user_id == user_id
        ).all()
        
        # Combine all podcast IDs the user has engaged with
        engaged_podcast_ids = set()
        engaged_podcast_ids.update([podcast_id for (podcast_id, _) in high_completion_podcasts])
        engaged_podcast_ids.update([podcast_id for (podcast_id,) in liked_podcasts])
        engaged_podcast_ids.update([podcast_id for (podcast_id,) in commented_podcasts])
        
        # --- 2. Get categories the user is interested in ---
        
        # Get categories from podcasts the user has engaged with
        interested_categories = db.query(
            Category.id, Category.name
        ).select_from(
            Podcast
        ).join(
            Podcast.categories
        ).filter(
            Podcast.id.in_(engaged_podcast_ids)
        ).distinct().all()
        
        interested_category_ids = [cat_id for (cat_id, _) in interested_categories]
        
        # --- 3. Build recommendations based on different factors ---
        
        # Weight for each recommendation type (can be adjusted)
        weights = {
            'podcast_engagement': 4,  # Higher weight for podcasts the user has engaged with
            'similar_categories': 3,  # Medium weight for similar categories
            'popular_overall': 1,     # Lower weight for generally popular content
            'recency': 2              # Medium weight for recently published content
        }
        
        # Base filter conditions - used in all queries
        base_conditions = []
        
        # Apply category filter if specified
        if category_id is not None:
            # Import the join table model for category filtering
            from app.models.podcast import podcast_categories
            base_conditions.append(
                Episode.podcast_id.in_(
                    db.query(podcast_categories.c.podcast_id).filter(
                        podcast_categories.c.category_id == category_id
                    )
                )
            )
        
        # Exclude already listened episodes if requested
        if exclude_listened and streamed_episode_ids:
            base_conditions.append(~Episode.id.in_(streamed_episode_ids))
        
        # Get recommendations from podcasts the user has engaged with
        engagement_recs = db.query(
            Episode,
            literal(weights['podcast_engagement']).label('score')
        ).filter(
            Episode.podcast_id.in_(engaged_podcast_ids),
            *base_conditions
        ).order_by(
            desc(Episode.published_at)
        ).limit(limit * 2).all()
        
        # Get recommendations from similar categories
        if interested_category_ids:
            # Import the join table model to properly join categories
            from app.models.podcast import podcast_categories
            
            category_recs = db.query(
                Episode,
                literal(weights['similar_categories']).label('score')
            ).join(
                Podcast, Episode.podcast_id == Podcast.id
            ).join(
                podcast_categories, Podcast.id == podcast_categories.c.podcast_id
            ).filter(
                podcast_categories.c.category_id.in_(interested_category_ids),
                ~Episode.podcast_id.in_(engaged_podcast_ids),
                *base_conditions
            ).order_by(
                desc(Episode.published_at)
            ).limit(limit * 2).all()
        else:
            category_recs = []
        
        # Get generally popular episodes that are recent
        one_month_ago = datetime.now() - timedelta(days=30)
        popular_recs = db.query(
            Episode,
            (literal(weights['popular_overall']) * func.count(Stream.id)).label('score')
        ).join(
            Stream, Stream.episode_id == Episode.id
        ).filter(
            Episode.published_at >= one_month_ago,
            *base_conditions
        ).group_by(
            Episode.id
        ).order_by(
            desc('score')
        ).limit(limit).all()
        
        # Get newest episodes from any podcast
        recency_recs = db.query(
            Episode,
            literal(weights['recency']).label('score')
        ).filter(
            Episode.published_at >= one_month_ago,
            *base_conditions
        ).order_by(
            desc(Episode.published_at)
        ).limit(limit).all()
        
        # --- 4. Combine all recommendations and rank them ---
        
        # Combine all recommendation types
        all_recs = []
        all_recs.extend([(episode, score) for episode, score in engagement_recs])
        all_recs.extend([(episode, score) for episode, score in category_recs])
        all_recs.extend([(episode, score) for episode, score in popular_recs])
        all_recs.extend([(episode, score) for episode, score in recency_recs])
        
        # De-duplicate by episode ID and sort by score
        seen_episodes = set()
        unique_recs = []
        
        for episode, score in sorted(all_recs, key=lambda x: x[1], reverse=True):
            if episode.id not in seen_episodes:
                seen_episodes.add(episode.id)
                unique_recs.append((episode, score))
        
        # Get the top recommendations based on limit
        final_recs = unique_recs[:limit]
        
        # --- 5. Format results ---
        result = []
        for episode, score in final_recs:
            recommendation = {
                "episode_id": episode.id,
                "title": episode.title,
                "description": episode.description,
                "podcast_id": episode.podcast_id,
                "audio_url": episode.audio_url,
                "cover_image": episode.cover_image,
                "duration": episode.duration,
                "published_at": episode.published_at.isoformat(),
                "recommendation_score": float(score)
            }
            
            # Add recommendation reason if requested
            if include_reasons:
                recommendation["recommendation_reason"] = StreamRepository.get_recommendation_reason(db, episode, user_id)
            
            result.append(recommendation)
        
        return result

    @staticmethod
    def get_recommendation_reason(db: Session, episode: Episode, user_id: int) -> str:
        """
        Generate a human-readable reason for why this content is being recommended.
        """
        # Check if user has streamed other episodes from this podcast
        other_episode_streams = db.query(Stream).join(
            Episode, Stream.episode_id == Episode.id
        ).filter(
            Stream.user_id == user_id,
            Episode.podcast_id == episode.podcast_id,
            Episode.id != episode.id
        ).first()
        
        if other_episode_streams:
            return "Because you listened to other episodes from this podcast"
        
        # Check if user has liked this podcast
        user_like = db.query(PodcastLike).filter(
            PodcastLike.user_id == user_id,
            PodcastLike.podcast_id == episode.podcast_id
        ).first()
        
        if user_like:
            return "Because you liked this podcast"
        
        # Check if this is a popular episode
        stream_count = db.query(func.count(Stream.id)).filter(
            Stream.episode_id == episode.id
        ).scalar()
        
        if stream_count > 10:  # Arbitrary threshold for "popular"
            return "Popular with other listeners"
        
        # Check if this is a new episode from a podcast with the same categories
        podcast = db.query(Podcast).filter(Podcast.id == episode.podcast_id).first()
        if podcast and podcast.categories:
            return "Similar to podcasts you enjoy"
        
        # Default reason
        if (datetime.now() - episode.published_at).days < 30:
            return "New release that might interest you"
        
        return "Recommended based on your listening history"

    @staticmethod
    def get_recently_played_episodes(
        db: Session,
        user_id: int,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recently played episodes for a user.
        
        Args:
            db: Database session
            user_id: User ID to get recently played episodes for
            limit: Maximum number of episodes to return
            days: Number of days to look back for recently played episodes
            
        Returns:
            List of dictionaries containing episode information and playback details
        """
        # Calculate the date threshold
        date_threshold = datetime.now() - timedelta(days=days)
        
        # Query for recently played episodes
        recent_episodes = db.query(
            Episode,
            Stream.last_position,
            Stream.duration_seconds,
            Stream.completed,
            Stream.created_at
        ).join(
            Stream, Stream.episode_id == Episode.id
        ).filter(
            Stream.user_id == user_id,
            Stream.created_at >= date_threshold
        ).order_by(
            desc(Stream.created_at)
        ).limit(limit).all()
        
        # Format the results
        result = []
        for episode, last_position, duration_seconds, completed, created_at in recent_episodes:
            result.append({
                "episode_id": episode.id,
                "title": episode.title,
                "description": episode.description,
                "podcast_id": episode.podcast_id,
                "audio_url": episode.audio_url,
                "cover_image": episode.cover_image,
                "duration": episode.duration,
                "last_position": last_position,
                "duration_seconds": duration_seconds,
                "completed": completed,
                "played_at": created_at.isoformat(),
                "progress_percentage": (last_position / episode.duration * 100) if episode.duration > 0 else 0
            })
        
        return result 