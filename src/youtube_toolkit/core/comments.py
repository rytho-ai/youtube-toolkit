"""
Advanced Comment Models for YouTube Toolkit.

This module provides enhanced comment functionality with pagination, filtering,
analytics, and comprehensive comment management.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from .dict_access import DictAccessMixin


class CommentOrder(Enum):
    """Comment ordering options."""
    RELEVANCE = "relevance"
    TIME = "time"
    RATING = "rating"


class CommentModerationStatus(Enum):
    """Comment moderation status."""
    PUBLISHED = "published"
    HELD_FOR_REVIEW = "heldForReview"
    LIKELY_SPAM = "likelySpam"
    REJECTED = "rejected"


class CommentTextFormat(Enum):
    """Comment text format options."""
    HTML = "html"
    PLAIN_TEXT = "plainText"


@dataclass
class CommentAuthor:
    """Comment author information."""
    display_name: str
    profile_image_url: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    is_verified: bool = False
    is_channel_owner: bool = False
    
    @property
    def is_verified_creator(self) -> bool:
        """Check if author is a verified creator."""
        return self.is_verified or self.is_channel_owner


@dataclass
class CommentMetrics:
    """Comment engagement metrics."""
    like_count: int = 0
    reply_count: int = 0
    total_reply_count: int = 0
    updated_at: Optional[datetime] = None
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score based on likes and replies."""
        if self.total_reply_count == 0:
            return float(self.like_count)
        return float(self.like_count) + (self.total_reply_count * 0.5)


@dataclass
class Comment:
    """Individual comment with enhanced metadata."""
    comment_id: str
    text: str
    author: CommentAuthor
    published_at: datetime
    updated_at: Optional[datetime] = None
    metrics: CommentMetrics = field(default_factory=CommentMetrics)
    moderation_status: CommentModerationStatus = CommentModerationStatus.PUBLISHED
    parent_id: Optional[str] = None
    video_id: Optional[str] = None
    replies: List['Comment'] = field(default_factory=list)
    
    @property
    def is_top_level(self) -> bool:
        """Check if this is a top-level comment."""
        return self.parent_id is None
    
    @property
    def is_reply(self) -> bool:
        """Check if this is a reply to another comment."""
        return self.parent_id is not None
    
    @property
    def has_replies(self) -> bool:
        """Check if this comment has replies."""
        return len(self.replies) > 0
    
    @property
    def total_engagement(self) -> int:
        """Get total engagement (likes + replies)."""
        return self.metrics.like_count + self.metrics.total_reply_count
    
    def add_reply(self, reply: 'Comment') -> None:
        """Add a reply to this comment."""
        reply.parent_id = self.comment_id
        self.replies.append(reply)
        self.metrics.reply_count = len(self.replies)
    
    def get_all_replies(self) -> List['Comment']:
        """Get all replies recursively."""
        all_replies = []
        for reply in self.replies:
            all_replies.append(reply)
            all_replies.extend(reply.get_all_replies())
        return all_replies


@dataclass
class CommentFilters:
    """Advanced comment filtering options."""
    # Ordering
    order: CommentOrder = CommentOrder.RELEVANCE
    
    # Pagination
    page_token: Optional[str] = None
    max_results: int = 100
    
    # Text format
    text_format: CommentTextFormat = CommentTextFormat.PLAIN_TEXT
    
    # Moderation filtering
    moderation_status: Optional[CommentModerationStatus] = None
    
    # Search within comments
    search_terms: Optional[str] = None
    
    # Author filtering
    author_channel_id: Optional[str] = None
    
    # Date filtering
    published_after: Optional[datetime] = None
    published_before: Optional[datetime] = None
    
    # Engagement filtering
    min_likes: Optional[int] = None
    min_replies: Optional[int] = None
    
    # Reply filtering
    include_replies: bool = True
    max_replies_per_comment: int = 20
    
    def validate_filters(self) -> List[str]:
        """Validate filter combinations."""
        errors = []
        
        if not (1 <= self.max_results <= 100):
            errors.append("max_results must be between 1 and 100")
        
        if not (0 <= self.max_replies_per_comment <= 100):
            errors.append("max_replies_per_comment must be between 0 and 100")
        
        if self.published_after and self.published_before:
            if self.published_after >= self.published_before:
                errors.append("published_after must be before published_before")
        
        return errors


@dataclass
class CommentAnalytics:
    """Comment analytics and insights."""
    total_comments: int = 0
    total_replies: int = 0
    total_likes: int = 0
    unique_authors: int = 0
    top_authors: List[Dict[str, Any]] = field(default_factory=list)
    engagement_distribution: Dict[str, int] = field(default_factory=dict)
    sentiment_analysis: Optional[Dict[str, float]] = None
    most_liked_comments: List[Comment] = field(default_factory=list)
    most_replied_comments: List[Comment] = field(default_factory=list)
    time_distribution: Dict[str, int] = field(default_factory=dict)
    
    def calculate_engagement_rate(self) -> float:
        """Calculate overall engagement rate."""
        if self.total_comments == 0:
            return 0.0
        return (self.total_likes + self.total_replies) / self.total_comments
    
    def get_top_contributors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top comment contributors."""
        return self.top_authors[:limit]


@dataclass
class CommentResult(DictAccessMixin):
    """Comprehensive comment result with pagination and analytics."""
    comments: List[Comment] = field(default_factory=list)
    total_results: int = 0
    page_info: Dict[str, Any] = field(default_factory=dict)
    next_page_token: Optional[str] = None
    prev_page_token: Optional[str] = None
    filters_applied: Optional[CommentFilters] = None
    analytics: Optional[CommentAnalytics] = None
    quota_cost: int = 1  # Comments API costs 1 unit per request
    
    @property
    def has_more_pages(self) -> bool:
        """Check if there are more pages available."""
        return self.next_page_token is not None
    
    @property
    def comment_count(self) -> int:
        """Get number of comments in this result."""
        return len(self.comments)
    
    def get_top_level_comments(self) -> List[Comment]:
        """Get only top-level comments."""
        return [comment for comment in self.comments if comment.is_top_level]
    
    def get_replies_only(self) -> List[Comment]:
        """Get only reply comments."""
        return [comment for comment in self.comments if comment.is_reply]
    
    def get_comments_by_author(self, author_name: str) -> List[Comment]:
        """Get comments by specific author."""
        return [
            comment for comment in self.comments 
            if comment.author.display_name.lower() == author_name.lower()
        ]
    
    def get_high_engagement_comments(self, min_likes: int = 10) -> List[Comment]:
        """Get comments with high engagement."""
        return [
            comment for comment in self.comments 
            if comment.metrics.like_count >= min_likes
        ]
    
    def search_comments(self, search_term: str) -> List[Comment]:
        """Search within comment text."""
        search_lower = search_term.lower()
        return [
            comment for comment in self.comments 
            if search_lower in comment.text.lower()
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'comments': [
                {
                    'comment_id': comment.comment_id,
                    'text': comment.text,
                    'author': {
                        'display_name': comment.author.display_name,
                        'profile_image_url': comment.author.profile_image_url,
                        'channel_id': comment.author.channel_id,
                        'is_verified': comment.author.is_verified,
                        'is_channel_owner': comment.author.is_channel_owner
                    },
                    'published_at': comment.published_at.isoformat(),
                    'updated_at': comment.updated_at.isoformat() if comment.updated_at else None,
                    'metrics': {
                        'like_count': comment.metrics.like_count,
                        'reply_count': comment.metrics.reply_count,
                        'total_reply_count': comment.metrics.total_reply_count,
                        'engagement_score': comment.metrics.engagement_score
                    },
                    'moderation_status': comment.moderation_status.value,
                    'parent_id': comment.parent_id,
                    'video_id': comment.video_id,
                    'replies': [
                        {
                            'comment_id': reply.comment_id,
                            'text': reply.text,
                            'author': {'display_name': reply.author.display_name},
                            'published_at': reply.published_at.isoformat(),
                            'metrics': {'like_count': reply.metrics.like_count}
                        } for reply in comment.replies
                    ]
                } for comment in self.comments
            ],
            'total_results': self.total_results,
            'page_info': self.page_info,
            'next_page_token': self.next_page_token,
            'prev_page_token': self.prev_page_token,
            'quota_cost': self.quota_cost,
            'analytics': {
                'total_comments': self.analytics.total_comments if self.analytics else 0,
                'total_replies': self.analytics.total_replies if self.analytics else 0,
                'total_likes': self.analytics.total_likes if self.analytics else 0,
                'engagement_rate': self.analytics.calculate_engagement_rate() if self.analytics else 0.0
            } if self.analytics else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommentResult':
        """Create CommentResult from dictionary."""
        # This would parse the dictionary back to CommentResult
        # Implementation would be similar to SearchResult.from_dict()
        pass


class CommentSentimentAnalyzer:
    """Simple sentiment analysis for comments."""
    
    POSITIVE_WORDS = {
        'great', 'awesome', 'amazing', 'love', 'best', 'excellent', 'fantastic',
        'wonderful', 'perfect', 'brilliant', 'outstanding', 'incredible'
    }
    
    NEGATIVE_WORDS = {
        'terrible', 'awful', 'hate', 'worst', 'bad', 'horrible', 'disgusting',
        'stupid', 'idiot', 'trash', 'garbage', 'pathetic', 'useless'
    }
    
    @classmethod
    def analyze_sentiment(cls, text: str) -> Dict[str, float]:
        """Analyze sentiment of comment text."""
        text_lower = text.lower()
        words = text_lower.split()
        
        positive_count = sum(1 for word in words if word in cls.POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in cls.NEGATIVE_WORDS)
        total_words = len(words)
        
        if total_words == 0:
            return {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        
        positive_score = positive_count / total_words
        negative_score = negative_count / total_words
        neutral_score = 1.0 - positive_score - negative_score
        
        return {
            'positive': positive_score,
            'negative': negative_score,
            'neutral': max(0.0, neutral_score)
        }
    
    @classmethod
    def get_sentiment_label(cls, sentiment_scores: Dict[str, float]) -> str:
        """Get sentiment label from scores."""
        if sentiment_scores['positive'] > sentiment_scores['negative']:
            return 'positive'
        elif sentiment_scores['negative'] > sentiment_scores['positive']:
            return 'negative'
        else:
            return 'neutral'