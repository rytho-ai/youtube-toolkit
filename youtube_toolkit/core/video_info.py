"""
Core VideoInfo dataclass for standardized video information.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .dict_access import DictAccessMixin


@dataclass
class VideoInfo(DictAccessMixin):
    """Standardized video information structure."""

    title: str
    duration: int
    views: int
    author: str
    video_id: str
    url: str

    # Optional fields for additional metadata
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    published_date: Optional[str] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    # Optional extras (populated when include= is used)
    chapters: Optional[List[Dict[str, Any]]] = None
    heatmap: Optional[List[Dict[str, Any]]] = None
    key_moments: Optional[List[Dict[str, Any]]] = None
    transcript: Optional[str] = None
    lyrics: Optional[str] = None
    
    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure duration is positive
        if self.duration < 0:
            self.duration = 0
        
        # Ensure views is non-negative
        if self.views < 0:
            self.views = 0
        
        # Clean title (remove extra whitespace)
        if self.title:
            self.title = self.title.strip()
        
        # Clean author (remove extra whitespace)
        if self.author:
            self.author = self.author.strip()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easy serialization."""
        result = {
            'title': self.title,
            'duration': self.duration,
            'views': self.views,
            'author': self.author,
            'video_id': self.video_id,
            'url': self.url,
            'description': self.description,
            'thumbnail': self.thumbnail,
            'category': self.category,
            'tags': self.tags,
            'published_date': self.published_date,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
        }
        # Include extras if present
        if self.chapters is not None:
            result['chapters'] = self.chapters
        if self.heatmap is not None:
            result['heatmap'] = self.heatmap
        if self.key_moments is not None:
            result['key_moments'] = self.key_moments
        if self.transcript is not None:
            result['transcript'] = self.transcript
        if self.lyrics is not None:
            result['lyrics'] = self.lyrics
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VideoInfo':
        """Create VideoInfo from dictionary."""
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation for easy debugging."""
        return f"VideoInfo(title='{self.title}', duration={self.duration}s, author='{self.author}')"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"VideoInfo(title='{self.title}', duration={self.duration}, views={self.views}, author='{self.author}', video_id='{self.video_id}', url='{self.url}')"
