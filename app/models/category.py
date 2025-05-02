from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    color = Column(String(20), nullable=False)  # Store hex color code
    icon = Column(String(50), nullable=True)  # Store icon name

    # Many-to-many relationship with podcasts
    podcasts = relationship(
        "Podcast",
        secondary="podcast_categories",
        back_populates="categories"
    )


# Association table for the many-to-many relationship between Podcast and Category
podcast_categories = Table(
    "podcast_categories",
    Base.metadata,
    Column("podcast_id", Integer, ForeignKey("podcasts.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True)
)