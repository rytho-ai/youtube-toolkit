"""
Core SearchResult dataclass for standardized search results.
Enhanced to support YouTube API v3 structure with thumbnails, live content, and advanced filtering.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import urllib.parse
from .video_info import VideoInfo
from .dict_access import DictAccessMixin


class BooleanSearchQuery:
    """Helper class for building Boolean search queries with NOT (-) and OR (|) operators."""
    
    def __init__(self):
        self.terms = []
        self.excluded_terms = []
        self.or_groups = []
    
    def add_term(self, term: str) -> 'BooleanSearchQuery':
        """Add a search term."""
        self.terms.append(term)
        return self
    
    def add_excluded_term(self, term: str) -> 'BooleanSearchQuery':
        """Add an excluded term (NOT operator)."""
        self.excluded_terms.append(term)
        return self
    
    def add_or_group(self, terms: List[str]) -> 'BooleanSearchQuery':
        """Add a group of terms connected with OR operator."""
        self.or_groups.append(terms)
        return self
    
    def build_query(self) -> str:
        """Build the final search query string."""
        query_parts = []
        
        # Add main terms
        if self.terms:
            query_parts.extend(self.terms)
        
        # Add OR groups
        for or_group in self.or_groups:
            or_query = "|".join(or_group)
            query_parts.append(f"({or_query})")
        
        # Add excluded terms
        for excluded in self.excluded_terms:
            query_parts.append(f"-{excluded}")
        
        return " ".join(query_parts)
    
    def encode_for_api(self) -> str:
        """Encode the query for API use (URL encoding)."""
        query = self.build_query()
        return urllib.parse.quote(query)
    
    @classmethod
    def from_string(cls, query_string: str) -> 'BooleanSearchQuery':
        """Create BooleanSearchQuery from a string with operators."""
        boolean_query = cls()
        
        # Simple parsing - in real implementation, you'd want more sophisticated parsing
        parts = query_string.split()
        
        for part in parts:
            if part.startswith('-'):
                boolean_query.add_excluded_term(part[1:])
            elif '|' in part:
                # Handle OR groups
                or_terms = part.strip('()').split('|')
                boolean_query.add_or_group(or_terms)
            else:
                boolean_query.add_term(part)
        
        return boolean_query
    
    def __str__(self) -> str:
        return self.build_query()


# YouTube Category IDs (commonly used ones)
YOUTUBE_CATEGORIES = {
    "Film & Animation": "1",
    "Autos & Vehicles": "2", 
    "Music": "10",
    "Pets & Animals": "15",
    "Sports": "17",
    "Short Movies": "18",
    "Travel & Events": "19",
    "Gaming": "20",
    "Videoblogging": "21",
    "People & Blogs": "22",
    "Comedy": "23",
    "Entertainment": "24",
    "News & Politics": "25",
    "Howto & Style": "26",
    "Education": "27",
    "Science & Technology": "28",
    "Nonprofits & Activism": "29",
    "Movies": "30",
    "Anime/Animation": "31",
    "Action/Adventure": "32",
    "Classics": "33",
    "Comedy": "34",
    "Documentary": "35",
    "Drama": "36",
    "Family": "37",
    "Foreign": "38",
    "Horror": "39",
    "Sci-Fi/Fantasy": "40",
    "Thriller": "41",
    "Shorts": "42",
    "Shows": "43",
    "Trailers": "44"
}


@dataclass
class Thumbnail:
    """YouTube thumbnail information."""
    url: str
    width: int
    height: int


@dataclass
class Thumbnails:
    """Collection of thumbnails in different resolutions."""
    default: Optional[Thumbnail] = None
    medium: Optional[Thumbnail] = None
    high: Optional[Thumbnail] = None
    standard: Optional[Thumbnail] = None
    maxres: Optional[Thumbnail] = None
    
    def get_best_thumbnail(self) -> Optional[Thumbnail]:
        """Get the highest quality thumbnail available."""
        for thumbnail in [self.maxres, self.standard, self.high, self.medium, self.default]:
            if thumbnail:
                return thumbnail
        return None
    
    def get_thumbnail_by_size(self, preferred_width: int = 320) -> Optional[Thumbnail]:
        """Get thumbnail closest to preferred width."""
        available = [t for t in [self.default, self.medium, self.high, self.standard, self.maxres] if t]
        if not available:
            return None
        
        # Find closest match
        closest = min(available, key=lambda t: abs(t.width - preferred_width))
        return closest


@dataclass
class SearchResultItem:
    """Individual search result item matching YouTube API structure."""
    kind: str  # youtube#video, youtube#channel, youtube#playlist
    etag: str
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    playlist_id: Optional[str] = None
    title: str = ""
    description: str = ""
    channel_title: str = ""
    published_at: Optional[datetime] = None
    thumbnails: Optional[Thumbnails] = None
    live_broadcast_content: str = "none"  # none, upcoming, live
    
    @property
    def is_live(self) -> bool:
        """Check if this is live content."""
        return self.live_broadcast_content == "live"
    
    @property
    def is_upcoming(self) -> bool:
        """Check if this is upcoming live content."""
        return self.live_broadcast_content == "upcoming"
    
    @property
    def is_live_content(self) -> bool:
        """Check if this is any type of live content."""
        return self.live_broadcast_content in ["live", "upcoming"]


@dataclass
class SearchFilters:
    """Advanced search filters matching YouTube API capabilities."""
    # Resource type filtering
    type: str = "video"  # video, channel, playlist, or any combination
    
    # Channel filtering
    channel_id: Optional[str] = None
    channel_type: Optional[str] = None  # any, show
    
    # Date filtering
    published_after: Optional[datetime] = None
    published_before: Optional[datetime] = None
    
    # Duration filtering
    video_duration: Optional[str] = None  # any, short, medium, long
    
    # Definition filtering
    video_definition: Optional[str] = None  # any, high, standard
    
    # Dimension filtering
    video_dimension: Optional[str] = None  # any, 2d, 3d
    
    # Caption filtering
    video_caption: Optional[str] = None  # any, closedCaption, none
    
    # License filtering
    video_license: Optional[str] = None  # any, creativeCommon, youtube
    
    # Embeddable filtering
    video_embeddable: Optional[str] = None  # any, true
    
    # Syndicated filtering
    video_syndicated: Optional[str] = None  # any, true
    
    # Type filtering
    video_type: Optional[str] = None  # any, episode, movie
    
    # NEW: Event type filtering (for live broadcasts)
    event_type: Optional[str] = None  # completed, live, upcoming
    
    # NEW: Content ownership filtering
    for_content_owner: Optional[bool] = None  # True for content owner videos
    for_developer: Optional[bool] = None  # True for developer-uploaded videos
    for_mine: Optional[bool] = None  # True for authenticated user's videos
    on_behalf_of_content_owner: Optional[str] = None  # Content owner ID
    
    # NEW: Video category filtering
    video_category_id: Optional[str] = None  # YouTube category ID
    
    # NEW: Paid promotion filtering
    video_paid_product_placement: Optional[str] = None  # any, true
    
    # NEW: Topic filtering
    topic_id: Optional[str] = None  # Curated topic ID
    
    # Ordering
    order: str = "relevance"  # relevance, date, rating, viewCount, title, videoCount
    
    # Location and language
    location: Optional[str] = None  # latitude,longitude
    location_radius: Optional[str] = None  # radius in meters
    relevance_language: Optional[str] = None  # language code
    
    # Region and language
    region_code: Optional[str] = None  # country code
    safe_search: Optional[str] = None  # moderate, none, strict
    
    # NEW: Pagination
    page_token: Optional[str] = None  # For pagination
    max_results: int = 20  # Maximum results per page (1-50)
    
    def validate_filters(self) -> List[str]:
        """Validate filter combinations and return any errors."""
        errors = []
        
        # Event type requires video type
        if self.event_type and self.type != "video":
            errors.append("eventType parameter requires type='video'")
        
        # Content owner filters require video type
        if (self.for_content_owner or self.for_mine) and self.type != "video":
            errors.append("forContentOwner and forMine parameters require type='video'")
        
        # Content owner filters conflict with video filters
        if self.for_content_owner and any([
            self.video_definition, self.video_dimension, self.video_duration,
            self.video_embeddable, self.video_license, self.video_syndicated,
            self.video_type
        ]):
            errors.append("forContentOwner cannot be used with video-specific filters")
        
        # Mine filter conflicts with video filters
        if self.for_mine and any([
            self.video_definition, self.video_dimension, self.video_duration,
            self.video_embeddable, self.video_license, self.video_syndicated,
            self.video_type
        ]):
            errors.append("forMine cannot be used with video-specific filters")
        
        # Video-specific filters require video type
        video_filters = [
            self.video_caption, self.video_category_id, self.video_definition,
            self.video_dimension, self.video_duration, self.video_embeddable,
            self.video_license, self.video_paid_product_placement,
            self.video_syndicated, self.video_type, self.event_type
        ]
        if any(video_filters) and self.type != "video":
            errors.append("Video-specific filters require type='video'")
        
        # Location requires video type
        if (self.location or self.location_radius) and self.type != "video":
            errors.append("Location parameters require type='video'")
        
        # Max results validation
        if not (1 <= self.max_results <= 50):
            errors.append("max_results must be between 1 and 50")
        
        return errors


@dataclass
class SearchResult(DictAccessMixin):
    """Enhanced search result structure with YouTube API v3 compatibility."""
    
    # Core results
    items: List[SearchResultItem] = field(default_factory=list)
    total_results: int = 0
    query: str = ""
    
    # Search metadata
    filters_applied: Optional[SearchFilters] = None
    search_time: Optional[float] = None
    backend_used: Optional[str] = None
    
    # Legacy compatibility
    videos: List[VideoInfo] = field(default_factory=list)
    
    # Pagination
    next_page_token: Optional[str] = None
    prev_page_token: Optional[str] = None
    
    def __post_init__(self):
        """Validate and clean data after initialization."""
        # Ensure items is a list
        if not isinstance(self.items, list):
            self.items = list(self.items) if self.items else []
        
        # Ensure videos is a list (legacy compatibility)
        if not isinstance(self.videos, list):
            self.videos = list(self.videos) if self.videos else []
        
        # Ensure total_results is non-negative
        if self.total_results < 0:
            self.total_results = 0
        
        # Clean query (remove extra whitespace)
        if self.query:
            self.query = self.query.strip()
        
        # Auto-populate legacy videos from items if needed
        if not self.videos and self.items:
            self._populate_legacy_videos()
    
    def _populate_legacy_videos(self):
        """Populate legacy videos list from items for backward compatibility."""
        from .video_info import VideoInfo
        
        for item in self.items:
            if item.kind == "youtube#video" and item.video_id:
                try:
                    video_info = VideoInfo(
                        video_id=item.video_id,
                        title=item.title,
                        author=item.channel_title,
                        duration=0,  # Will be populated by actual video info fetch
                        views=0,     # Will be populated by actual video info fetch
                        upload_date=str(item.published_at) if item.published_at else "",
                        description=item.description,
                        watch_url=f"https://www.youtube.com/watch?v={item.video_id}"
                    )
                    self.videos.append(video_info)
                except Exception:
                    # Silently skip legacy VideoInfo creation - this is backwards compatibility
                    # The modern SearchResultItem structure is used instead
                    pass
    
    @property
    def count(self) -> int:
        """Get the number of items in this result."""
        return len(self.items)
    
    @property
    def has_results(self) -> bool:
        """Check if there are any items in this result."""
        return len(self.items) > 0
    
    @property
    def video_count(self) -> int:
        """Get the number of video items specifically."""
        return len([item for item in self.items if item.kind == "youtube#video"])
    
    @property
    def channel_count(self) -> int:
        """Get the number of channel items specifically."""
        return len([item for item in self.items if item.kind == "youtube#channel"])
    
    @property
    def playlist_count(self) -> int:
        """Get the number of playlist items specifically."""
        return len([item for item in self.items if item.kind == "youtube#playlist"])
    
    @property
    def live_content_count(self) -> int:
        """Get the number of live content items."""
        return len([item for item in self.items if item.is_live_content])
    
    def get_video_by_title(self, title: str) -> Optional[VideoInfo]:
        """Find a video by title (case-insensitive)."""
        title_lower = title.lower()
        for video in self.videos:
            if video.title.lower() == title_lower:
                return video
        return None
    
    def get_videos_by_author(self, author: str) -> List[VideoInfo]:
        """Find videos by author (case-insensitive)."""
        author_lower = author.lower()
        return [video for video in self.videos if video.author.lower() == author_lower]
    
    def filter_by_duration(self, max_duration: int) -> List[VideoInfo]:
        """Filter videos by maximum duration in seconds."""
        return [video for video in self.videos if video.duration <= max_duration]
    
    def sort_by_views(self, reverse: bool = True) -> List[VideoInfo]:
        """Sort videos by view count."""
        return sorted(self.videos, key=lambda x: x.views, reverse=reverse)
    
    def sort_by_duration(self, reverse: bool = False) -> List[VideoInfo]:
        """Sort videos by duration."""
        return sorted(self.videos, key=lambda x: x.duration, reverse=reverse)
    
    # Enhanced methods for new SearchResultItem structure
    
    def get_items_by_type(self, item_type: str) -> List[SearchResultItem]:
        """Get items filtered by type (video, channel, playlist)."""
        return [item for item in self.items if item.kind == f"youtube#{item_type}"]
    
    def get_live_content(self) -> List[SearchResultItem]:
        """Get all live content items (live and upcoming)."""
        return [item for item in self.items if item.is_live_content]
    
    def get_live_streams(self) -> List[SearchResultItem]:
        """Get currently live streams."""
        return [item for item in self.items if item.is_live]
    
    def get_upcoming_streams(self) -> List[SearchResultItem]:
        """Get upcoming live streams."""
        return [item for item in self.items if item.is_upcoming]
    
    def get_items_by_channel(self, channel_title: str) -> List[SearchResultItem]:
        """Get items from a specific channel."""
        channel_lower = channel_title.lower()
        return [item for item in self.items if item.channel_title.lower() == channel_lower]
    
    def get_items_with_thumbnails(self, min_width: int = 120) -> List[SearchResultItem]:
        """Get items that have thumbnails meeting minimum width requirement."""
        result = []
        for item in self.items:
            if item.thumbnails:
                best_thumbnail = item.thumbnails.get_best_thumbnail()
                if best_thumbnail and best_thumbnail.width >= min_width:
                    result.append(item)
        return result
    
    def sort_by_published_date(self, reverse: bool = True) -> List[SearchResultItem]:
        """Sort items by published date."""
        return sorted(
            [item for item in self.items if item.published_at], 
            key=lambda x: x.published_at, 
            reverse=reverse
        )
    
    def filter_by_date_range(self, start_date: datetime, end_date: datetime) -> List[SearchResultItem]:
        """Filter items by published date range."""
        return [
            item for item in self.items 
            if item.published_at and start_date <= item.published_at <= end_date
        ]
    
    def get_thumbnails_summary(self) -> Dict[str, int]:
        """Get summary of available thumbnail qualities."""
        summary = {"default": 0, "medium": 0, "high": 0, "standard": 0, "maxres": 0}
        
        for item in self.items:
            if item.thumbnails:
                if item.thumbnails.default:
                    summary["default"] += 1
                if item.thumbnails.medium:
                    summary["medium"] += 1
                if item.thumbnails.high:
                    summary["high"] += 1
                if item.thumbnails.standard:
                    summary["standard"] += 1
                if item.thumbnails.maxres:
                    summary["maxres"] += 1
        
        return summary
    
    def to_dict(self) -> dict:
        """Convert to dictionary for easy serialization."""
        return {
            'items': [
                {
                    'kind': item.kind,
                    'etag': item.etag,
                    'video_id': item.video_id,
                    'channel_id': item.channel_id,
                    'playlist_id': item.playlist_id,
                    'title': item.title,
                    'description': item.description,
                    'channel_title': item.channel_title,
                    'published_at': item.published_at.isoformat() if item.published_at else None,
                    'thumbnails': {
                        'default': {
                            'url': item.thumbnails.default.url,
                            'width': item.thumbnails.default.width,
                            'height': item.thumbnails.default.height
                        } if item.thumbnails and item.thumbnails.default else None,
                        'medium': {
                            'url': item.thumbnails.medium.url,
                            'width': item.thumbnails.medium.width,
                            'height': item.thumbnails.medium.height
                        } if item.thumbnails and item.thumbnails.medium else None,
                        'high': {
                            'url': item.thumbnails.high.url,
                            'width': item.thumbnails.high.width,
                            'height': item.thumbnails.high.height
                        } if item.thumbnails and item.thumbnails.high else None,
                        'standard': {
                            'url': item.thumbnails.standard.url,
                            'width': item.thumbnails.standard.width,
                            'height': item.thumbnails.standard.height
                        } if item.thumbnails and item.thumbnails.standard else None,
                        'maxres': {
                            'url': item.thumbnails.maxres.url,
                            'width': item.thumbnails.maxres.width,
                            'height': item.thumbnails.maxres.height
                        } if item.thumbnails and item.thumbnails.maxres else None,
                    } if item.thumbnails else None,
                    'live_broadcast_content': item.live_broadcast_content
                } for item in self.items
            ],
            'videos': [video.to_dict() for video in self.videos],  # Legacy compatibility
            'total_results': self.total_results,
            'query': self.query,
            'filters_applied': self.filters_applied.__dict__ if self.filters_applied else None,
            'search_time': self.search_time,
            'backend_used': self.backend_used,
            'next_page_token': self.next_page_token,
            'prev_page_token': self.prev_page_token,
            'count': self.count,
            'has_results': self.has_results,
            'video_count': self.video_count,
            'channel_count': self.channel_count,
            'playlist_count': self.playlist_count,
            'live_content_count': self.live_content_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SearchResult':
        """Create SearchResult from dictionary."""
        # Convert items back to SearchResultItem objects
        items_data = data.get('items', [])
        items = []
        
        for item_data in items_data:
            # Parse thumbnails
            thumbnails_data = item_data.get('thumbnails')
            thumbnails = None
            if thumbnails_data:
                thumbnails = Thumbnails(
                    default=Thumbnail(**thumbnails_data['default']) if thumbnails_data.get('default') else None,
                    medium=Thumbnail(**thumbnails_data['medium']) if thumbnails_data.get('medium') else None,
                    high=Thumbnail(**thumbnails_data['high']) if thumbnails_data.get('high') else None,
                    standard=Thumbnail(**thumbnails_data['standard']) if thumbnails_data.get('standard') else None,
                    maxres=Thumbnail(**thumbnails_data['maxres']) if thumbnails_data.get('maxres') else None,
                )
            
            # Parse published_at
            published_at = None
            if item_data.get('published_at'):
                try:
                    published_at = datetime.fromisoformat(item_data['published_at'].replace('Z', '+00:00'))
                except:
                    pass
            
            item = SearchResultItem(
                kind=item_data.get('kind', 'youtube#video'),
                etag=item_data.get('etag', ''),
                video_id=item_data.get('video_id'),
                channel_id=item_data.get('channel_id'),
                playlist_id=item_data.get('playlist_id'),
                title=item_data.get('title', ''),
                description=item_data.get('description', ''),
                channel_title=item_data.get('channel_title', ''),
                published_at=published_at,
                thumbnails=thumbnails,
                live_broadcast_content=item_data.get('live_broadcast_content', 'none')
            )
            items.append(item)
        
        # Convert video dicts back to VideoInfo objects (legacy compatibility)
        videos_data = data.get('videos', [])
        videos = [VideoInfo.from_dict(video_data) for video_data in videos_data]
        
        # Parse filters
        filters_data = data.get('filters_applied')
        filters = None
        if filters_data:
            filters = SearchFilters(**filters_data)
        
        return cls(
            items=items,
            videos=videos,
            total_results=data.get('total_results', 0),
            query=data.get('query', ''),
            filters_applied=filters,
            search_time=data.get('search_time'),
            backend_used=data.get('backend_used'),
            next_page_token=data.get('next_page_token'),
            prev_page_token=data.get('prev_page_token')
        )
    
    def __str__(self) -> str:
        """String representation for easy debugging."""
        return f"SearchResult(query='{self.query}', items={self.count}/{self.total_results}, videos={self.video_count}, channels={self.channel_count}, playlists={self.playlist_count})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"SearchResult(items={self.count}, total_results={self.total_results}, query='{self.query}', backend_used='{self.backend_used}', live_content={self.live_content_count})"
