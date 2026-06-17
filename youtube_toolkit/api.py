"""
Main YouTube Toolkit interface.

This module provides a unified interface that combines all handlers
and implements fallback logic for robust YouTube operations.
"""

from typing import Optional, List, Dict, Any, Union
from .handlers.pytubefix_handler import PyTubeFixHandler
from .handlers.yt_dlp_handler import YTDLPHandler
from .handlers.youtube_api_handler import YouTubeAPIHandler
from .utils.anti_detection import AntiDetectionManager
from .core.video_info import VideoInfo
from .core.download import DownloadResult
from .core.search import SearchResult, SearchFilters, SearchResultItem
from .core.comments import CommentResult, CommentFilters, Comment, CommentAuthor, CommentMetrics, CommentOrder
from .core.captions import CaptionResult, CaptionFilters, CaptionTrack
from .services.analyze import AnalyzeService
from .services.system import SystemService
from .services.channel import ChannelService
from .services.get_info import GetInfoService
from .services.playlist import PlaylistService
from .services.comments import CommentsService
from .services.captions import CaptionsService
from .services.search import SearchService
from .services.download import DownloadService
import os
import time
import warnings


class YouTubeToolkit:
    """
    Main YouTube Toolkit class that combines multiple backends.

    This class orchestrates different handlers to provide robust
    YouTube functionality with automatic fallback.

    Consolidated API (v1.0) - Five Core Sub-APIs:
        toolkit = YouTubeToolkit()

        # GET - Retrieve information
        toolkit.get(url)                          # Smart auto-detect
        toolkit.get.video(url)                    # Video info
        toolkit.get.channel("@Fireship")          # Channel info
        toolkit.get.chapters(url)                 # Video chapters
        toolkit.get.formats(url)                  # Available formats
        toolkit.get.restriction(url)              # Age/region restrictions

        # DOWNLOAD - Save to disk
        toolkit.download(url)                     # Audio (default)
        toolkit.download.audio(url, format='mp3') # Explicit audio
        toolkit.download.video(url, quality='720p')
        toolkit.download.shorts(url)              # Download Shorts
        toolkit.download.live(url)                # Download live streams
        toolkit.download.with_sponsorblock(url)   # Skip sponsors

        # SEARCH - Find content
        toolkit.search("query")                   # Videos (default)
        toolkit.search.videos("query")
        toolkit.search.trending()                 # Trending videos
        toolkit.search.categories()               # Video categories

        # ANALYZE - Analyze content (NEW)
        toolkit.analyze(url)                      # Full metadata
        toolkit.analyze.engagement(url)           # Heatmap + key moments
        toolkit.analyze.sponsorblock(url)         # Sponsor segments
        toolkit.analyze.filesize(url)             # Filesize preview

        # STREAM - Stream to buffer (NEW)
        toolkit.stream(url)                       # Audio buffer
        toolkit.stream.audio(url)                 # Audio buffer
        toolkit.stream.video(url)                 # Video buffer
        toolkit.stream.live.status(url)           # Live stream status
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the YouTube Toolkit.

        Args:
            verbose: Whether to show detailed progress information
        """
        self.verbose = verbose

        # Create ONE anti-detection manager
        self.anti_detection = AntiDetectionManager()

        # Pass anti-detection to handlers that need it (not YouTube API)
        self.pytubefix = PyTubeFixHandler(self.anti_detection)
        self.ytdlp = YTDLPHandler(self.anti_detection)
        # Alias for backward compatibility
        self.yt_dlp = self.ytdlp
        # YouTube API doesn't need anti-detection (it's official)
        self.youtube_api = YouTubeAPIHandler()

        # Initialize domain services (business logic descended out of this
        # god class; api.py methods below are thin delegations to these).
        self._analyze = AnalyzeService(self)
        self._system = SystemService(self)
        self._channel = ChannelService(self)
        self._get_info = GetInfoService(self)
        self._playlist = PlaylistService(self)
        self._comments = CommentsService(self)
        self._captions = CaptionsService(self)
        self._search = SearchService(self)
        self._download = DownloadService(self)

        # Initialize Core Sub-APIs (v1.0 Consolidated - 5 Core APIs)
        from .sub_apis import GetAPI, DownloadAPI, SearchAPI, AnalyzeAPI, StreamAPI
        self.get = GetAPI(self)
        self.download = DownloadAPI(self)
        self.search = SearchAPI(self)
        self.analyze = AnalyzeAPI(self)
        self.stream = StreamAPI(self)
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information with automatic fallback.
        
        Tries pytubefix first, then falls back to yt-dlp.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video details
            
        Raises:
            RuntimeError: If all methods fail
        """
        return self._get_info.get_video_info(url)
    
    def download_audio(self, url: str, format: str = 'wav',
                       progress_callback: bool = True, prefer_yt_dlp: bool = False,
                       output_path: str = None, bitrate: str = '128k',
                       concurrent_fragments: int = 1) -> str:
        """
        Download audio with automatic fallback.

        Args:
            url: YouTube video URL
            format: Audio format ('wav', 'mp3', 'm4a')
            progress_callback: Whether to show download progress
            prefer_yt_dlp: Whether to prefer yt-dlp over pytubefix
            output_path: Custom output path for the audio file. If None, uses default location.
                         For pytubefix: full file path including filename
                         For yt-dlp: directory path (filename auto-generated)
            bitrate: Audio bitrate ('best', '320k', '256k', '192k', '128k', '96k', '64k')
            concurrent_fragments: Per-video fragment parallelism for the yt-dlp path
                (axis ①). Default 1 = current behaviour. Ignored on the pytubefix
                path (no equivalent).

        Returns:
            Path to downloaded audio file
        """
        return self._download.download_audio(
            url, format, progress_callback, prefer_yt_dlp, output_path, bitrate,
            concurrent_fragments=concurrent_fragments
        )
    
    def download_video(self, url: str, quality: str = 'best',
                       progress_callback: bool = True, prefer_yt_dlp: bool = True,
                       output_path: str = None, concurrent_fragments: int = 1) -> str:
        """
        Download video with automatic fallback.

        Args:
            url: YouTube video URL
            quality: Video quality ('best', '720p', '1080p', etc.')
            progress_callback: Whether to show download progress
            prefer_yt_dlp: Whether to prefer yt-dlp over pytubefix (default: True for reliability)
            output_path: Custom output path for the video file. If None, uses default location.
                         For pytubefix: full file path including filename
                         For yt-dlp: directory path (filename auto-generated)

        Returns:
            Path to downloaded video file

        Note:
            yt-dlp is now preferred by default due to better reliability and fewer
            broken pipe errors compared to PyTubeFix's MoviePy+ffmpeg combination.

            concurrent_fragments (default 1 = current behaviour) enables per-video
            fragment parallelism on the yt-dlp path only (axis ①); ignored on the
            pytubefix path.
        """
        return self._download.download_video(
            url, quality, progress_callback, prefer_yt_dlp, output_path,
            concurrent_fragments=concurrent_fragments
        )

    def download_many(self, urls, *, media_type: str = 'audio', format: str = 'wav',
                      quality: str = '720p', max_workers: int = 1,
                      **kwargs) -> List[Dict[str, Any]]:
        """
        Download multiple videos, optionally in parallel (Phase 5 axis ②).

        Conservative parallelism: ``max_workers=1`` (default) runs sequentially,
        identical to calling download_audio/download_video one URL at a time.
        ``max_workers>1`` fans out across a bounded thread pool, but every
        per-video download still goes through the api layer (handler fallback +
        the thread-safe ``@rate_limit``), so the rate limiter keeps pacing real
        requests even under fan-out — parallelism just means requests queue at the
        limiter rather than turning into bot-like bursts.

        Note: async/parallel never makes a *single* download faster; it lets a
        server/agent service several downloads without serializing on each.

        Args:
            urls: Iterable of video URLs.
            media_type: 'audio' or 'video'.
            format: Audio format (media_type='audio').
            quality: Video quality (media_type='video').
            max_workers: Parallelism cap; <=1 = sequential.
            **kwargs: Forwarded per-video options (output_path, bitrate,
                concurrent_fragments, prefer_yt_dlp, ...).

        Returns:
            List of dicts aligned to input order:
            ``{'url', 'success', 'path', 'error'}``.
        """
        return self._download.download_many(
            urls, media_type=media_type, format=format, quality=quality,
            max_workers=max_workers, **kwargs
        )

    def get_available_formats(self, url: str) -> Dict[str, Any]:
        """
        Get available download formats.
        
        Tries pytubefix first, then falls back to yt-dlp.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary of available formats
        """
        return self._get_info.get_available_formats(url)
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID string
        """
        # Try pytubefix method first
        try:
            return self.pytubefix.extract_video_id(url)
        except:
            pass
        
        # Fallback to yt-dlp method
        try:
            return self.yt_dlp.extract_video_id(url)
        except:
            pass
        
        # If both fail, raise error
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def get_video_description(self, url: str) -> str:
        """
        Get video description using yt-dlp.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video description text
        """
        return self._get_info.get_video_description(url)
    
    def test_handlers(self, url: str) -> Dict[str, bool]:
        """
        Test both handlers to see which ones are working.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with handler status
        """
        return self._system.test_handlers(url)
    
    def get_rich_metadata(self, url: str) -> Dict[str, Any]:
        """
        Get rich metadata using YouTube API.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with rich metadata
        """
        return self._get_info.get_rich_metadata(url)
    
    def get_comments(self, url: str, max_results: int = 100,
                     sort_by: str = 'relevance') -> List[Dict[str, Any]]:
        """
        Get video comments using YouTube API (legacy method for backward compatibility).
        
        Args:
            url: YouTube video URL
            max_results: Maximum number of comments to retrieve
            sort_by: Sort order ('relevance', 'time')
            
        Returns:
            List of comment dictionaries
        """
        return self._comments.get_comments(url, max_results=max_results, sort_by=sort_by)
    
    def advanced_get_comments(self, url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Advanced comment retrieval with comprehensive filtering, pagination, and analytics.
        
        Args:
            url: YouTube video URL
            filters: CommentFilters object or dict with advanced filtering options
            
        Returns:
            Dictionary with comprehensive comment results including analytics
        """
        return self._comments.advanced_get_comments(url, filters)
    
    def get_comments_paginated(self, url: str, page_token: Optional[str] = None,
                              max_results: int = 100, order: str = 'relevance') -> Dict[str, Any]:
        """
        Get comments with pagination support.
        
        Args:
            url: YouTube video URL
            page_token: Token for pagination (from previous result)
            max_results: Maximum number of comments per page
            order: Comment order ('relevance', 'time', 'rating')
            
        Returns:
            Dictionary with paginated comment results
        """
        return self._comments.get_comments_paginated(url, page_token, max_results, order)
    
    def search_comments(self, url: str, search_term: str, max_results: int = 100) -> Dict[str, Any]:
        """
        Search within video comments.
        
        Args:
            url: YouTube video URL
            search_term: Term to search for in comments
            max_results: Maximum number of comments to retrieve
            
        Returns:
            Dictionary with filtered comment results
        """
        return self._comments.search_comments(url, search_term, max_results)
    
    def get_high_engagement_comments(self, url: str, min_likes: int = 10,
                                   max_results: int = 50) -> Dict[str, Any]:
        """
        Get comments with high engagement (likes).
        
        Args:
            url: YouTube video URL
            min_likes: Minimum number of likes required
            max_results: Maximum number of comments to retrieve
            
        Returns:
            Dictionary with high engagement comment results
        """
        return self._comments.get_high_engagement_comments(url, min_likes, max_results)
    
    def get_comments_by_author(self, url: str, author_channel_id: str,
                              max_results: int = 100) -> Dict[str, Any]:
        """
        Get comments from a specific author.
        
        Args:
            url: YouTube video URL
            author_channel_id: Channel ID of the author
            max_results: Maximum number of comments to retrieve
            
        Returns:
            Dictionary with author-specific comment results
        """
        return self._comments.get_comments_by_author(url, author_channel_id, max_results)
    
    def get_recent_comments(self, url: str, days_back: int = 7,
                           max_results: int = 100) -> Dict[str, Any]:
        """
        Get recent comments from the last N days.
        
        Args:
            url: YouTube video URL
            days_back: Number of days to look back
            max_results: Maximum number of comments to retrieve
            
        Returns:
            Dictionary with recent comment results
        """
        return self._comments.get_recent_comments(url, days_back, max_results)
    
    def export_comments(self, url: str, format: str = 'json', 
                       output_path: Optional[str] = None, filters: Optional[Dict] = None) -> str:
        """
        Export comments to file (JSON or CSV).
        
        Args:
            url: YouTube video URL
            format: Export format ('json' or 'csv')
            output_path: Output file path (optional)
            filters: Optional comment filters
            
        Returns:
            Path to exported file
        """
        return self._comments.export_comments(url, format, output_path, filters)
    
    def display_comments(self, url: str, top_n: int = 3,
                        sort_by: str = 'relevance') -> None:
        """
        Display top comments for a video.
        
        Args:
            url: YouTube video URL
            top_n: Number of top comments to display
            sort_by: Sort order ('relevance', 'time')
        """
        return self._comments.display_comments(url, top_n, sort_by)
    
    def search_videos(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos (legacy method for backward compatibility).
        
        Args:
            query: Search query string
            filters: Optional filters for search results
            max_results: Maximum number of results to return
            
        Returns:
            List of video dictionaries with search results
        """
        return self._search.search_videos(query, filters, max_results)
    
    def advanced_search(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> Dict[str, Any]:
        """
        Advanced search with comprehensive filtering and rich results.
        
        Args:
            query: Search query string
            filters: SearchFilters object or dict with advanced filtering options
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with comprehensive search results including thumbnails, live content, etc.
        """
        return self._search.advanced_search(query, filters, max_results)
    
    def search_live_content(self, query: str, event_type: str = "live", max_results: int = 20) -> Dict[str, Any]:
        """
        Search specifically for live content (live streams, upcoming broadcasts).
        
        Args:
            query: Search query string
            event_type: Type of live content ('live', 'upcoming', 'completed')
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with live content search results
        """
        return self._search.search_live_content(query, event_type, max_results)
    
    def search_by_category(self, query: str, category_name: str, max_results: int = 20) -> Dict[str, Any]:
        """
        Search for videos in a specific YouTube category.
        
        Args:
            query: Search query string
            category_name: YouTube category name (e.g., 'Gaming', 'Music', 'Education')
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with category-filtered search results
        """
        return self._search.search_by_category(query, category_name, max_results)
    
    def search_sponsored_content(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """
        Search for videos with paid product placements (sponsored content).
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with sponsored content search results
        """
        return self._search.search_sponsored_content(query, max_results)
    
    def search_with_boolean_query(self, boolean_query: str, filters: Optional[Dict] = None, max_results: int = 20) -> Dict[str, Any]:
        """
        Search using Boolean operators (NOT -, OR |).
        
        Args:
            boolean_query: Query string with Boolean operators (e.g., "python -tutorial", "gaming|streaming")
            filters: Optional additional filters
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        return self._search.search_with_boolean_query(boolean_query, filters, max_results)
    
    def search_paginated(self, query: str, filters: Optional[Dict] = None, 
                        page_token: Optional[str] = None, max_results: int = 20) -> Dict[str, Any]:
        """
        Search with pagination support.
        
        Args:
            query: Search query string
            filters: Optional search filters
            page_token: Token for pagination (from previous search result)
            max_results: Maximum number of results per page
            
        Returns:
            Dictionary with paginated search results
        """
        return self._search.search_paginated(query, filters, page_token, max_results)
    
    def get_search_categories(self) -> Dict[str, str]:
        """
        Get available YouTube categories for filtering.
        
        Returns:
            Dictionary mapping category names to IDs
        """
        return self._search.get_search_categories()
    
    def get_captions(self, url: str) -> Dict[str, Any]:
        """
        Get available captions/subtitles for a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with caption information
        """
        return self._captions.get_captions(url)
    
    def download_captions(self, url: str, language_code: str = 'en', output_path: str = None) -> str:
        """
        Download captions with automatic fallback across handlers (legacy method for backward compatibility).
        
        Args:
            url: YouTube video URL
            language_code: Language code (e.g., 'en', 'es', 'fr')
            output_path: Output file path (optional)
            
        Returns:
            Path to downloaded caption file
        """
        return self._captions.download_captions(url, language_code, output_path)
    
    def list_captions(self, url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        List available caption tracks for a video with advanced filtering.
        
        Args:
            url: YouTube video URL
            filters: CaptionFilters object or dict with filtering options
            
        Returns:
            Dictionary with caption track information and analytics
        """
        return self._captions.list_captions(url, filters)
    
    def advanced_download_captions(self, url: str, language_code: str = 'en',
                                 format: str = 'srt', output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Advanced caption download with format conversion and analysis.
        
        Args:
            url: YouTube video URL
            language_code: Language code (e.g., 'en', 'es', 'fr')
            format: Output format ('srt', 'vtt', 'txt', 'ttml')
            output_path: Output file path (optional)
            
        Returns:
            Dictionary with download results and analysis
        """
        return self._captions.advanced_download_captions(url, language_code, format, output_path)
    
    def get_captions_in_format(self, url: str, language_code: str = 'en',
                              format: str = 'vtt') -> str:
        """
        Get captions in specific format (VTT, TXT, etc.).
        
        Args:
            url: YouTube video URL
            language_code: Language code
            format: Output format ('srt', 'vtt', 'txt')
            
        Returns:
            Caption content as string
        """
        return self._captions.get_captions_in_format(url, language_code, format)
    
    def search_captions(self, url: str, search_term: str, language_code: str = 'en') -> List[Dict[str, Any]]:
        """
        Search within caption content.
        
        Args:
            url: YouTube video URL
            search_term: Term to search for in captions
            language_code: Language code
            
        Returns:
            List of matching caption cues with timestamps
        """
        return self._captions.search_captions(url, search_term, language_code)
    
    def get_caption_analytics(self, url: str, language_code: str = 'en') -> Dict[str, Any]:
        """
        Get comprehensive caption analytics.
        
        Args:
            url: YouTube video URL
            language_code: Language code
            
        Returns:
            Dictionary with caption analytics
        """
        return self._captions.get_caption_analytics(url, language_code)
    
    def export_captions(self, url: str, format: str = 'json', 
                       output_path: Optional[str] = None, language_code: str = 'en') -> str:
        """
        Export captions with metadata and analysis.
        
        Args:
            url: YouTube video URL
            format: Export format ('json', 'csv', 'srt', 'vtt', 'txt')
            output_path: Output file path (optional)
            language_code: Language code
            
        Returns:
            Path to exported file
        """
        return self._captions.export_captions(url, format, output_path, language_code)
    
    def get_best_caption_track(self, url: str, preferred_language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Get the best available caption track for a video.
        
        Args:
            url: YouTube video URL
            preferred_language: Preferred language code
            
        Returns:
            Dictionary with best caption track information
        """
        return self._captions.get_best_caption_track(url, preferred_language)
    
    def get_anti_detection_status(self) -> Dict[str, Any]:
        """Get comprehensive anti-detection status."""
        return self._system.get_anti_detection_status()

    def test_anti_detection(self, url: str) -> Dict[str, Any]:
        """Test anti-detection system with a simple request."""
        return self._system.test_anti_detection(url)

    def test_search(self, query: str = "test") -> Dict[str, Any]:
        """
        Test search functionality across all handlers.

        Args:
            query: Test search query

        Returns:
            Dictionary with search test results
        """
        return self._system.test_search(query)
    
    def get_playlist_urls(self, playlist_url: str) -> List[str]:
        """
        Get video URLs from playlist with automatic fallback.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of video URLs
        """
        return self._playlist.get_playlist_urls(playlist_url)
    
    def download_playlist_media(self, playlist_url: str, media_type: str = 'audio',
                               format: str = 'wav', quality: str = 'best',
                               include_captions: bool = False, audio_bitrate: str = '128k',
                               max_workers: int = 1) -> Dict[str, Any]:
        """
        Download media from all videos in playlist.

        Args:
            playlist_url: YouTube playlist URL
            media_type: 'audio' or 'video'
            format: Audio format ('wav', 'mp3', 'm4a') or video quality ('best', '720p', '1080p')
            quality: Video quality (only used if media_type='video')
            include_captions: Whether to download captions for each video
            audio_bitrate: Audio bitrate ('best', '320k', '256k', '192k', '128k', '96k', '64k') - only used if media_type='audio'
            max_workers: Per-video parallelism (axis ②). Default 1 = current
                sequential behaviour. >1 fans per-video downloads out across a
                bounded thread pool; metadata structure and counts are unchanged.

        Returns:
            Dictionary with results summary
        """
        return self._playlist.download_playlist_media(
            playlist_url, media_type, format, quality, include_captions, audio_bitrate,
            max_workers=max_workers
        )
    
    def _sanitize_filename(self, filename: str) -> str:
        """Convert filename to safe format for file system."""
        import re
        # Remove/replace invalid characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return safe_name[:100].strip()

    # =========================================================================
    # CHANNEL SUPPORT (v0.3+)
    # These methods provide channel-related functionality.
    # =========================================================================

    def get_channel_videos(self, channel: str,
                           content_type: str = 'videos',
                           limit: Optional[int] = None,
                           sort_by: str = 'newest',
                           use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        """
        Get videos from a YouTube channel.

        Uses pytubefix by default. Set use_scrapetube=True for unlimited videos
        (requires scrapetube to be installed: pip install youtube-toolkit[scrapers]).

        Args:
            channel: Channel URL (@handle, /channel/ID, or full URL)
            content_type: 'videos', 'shorts', 'live', or 'playlists'
            limit: Maximum number of items (None = all available)
            sort_by: Sort order - 'newest', 'oldest', or 'popular'
            use_scrapetube: Use scrapetube for unlimited results (optional dependency)

        Returns:
            List of video/playlist info dicts

        Example:
            >>> videos = toolkit.get_channel_videos("@Fireship", limit=50)
            >>> shorts = toolkit.get_channel_videos("@Fireship", content_type='shorts')
            >>> # For unlimited videos (requires scrapetube)
            >>> all_videos = toolkit.get_channel_videos("@Fireship", use_scrapetube=True)
        """
        return self._channel.get_channel_videos(channel, content_type, limit, sort_by, use_scrapetube)

    def get_channel_info(self, channel_url: str) -> Dict[str, Any]:
        """
        Get channel metadata without API quota.

        Args:
            channel_url: YouTube channel URL (@handle, /channel/ID, or full URL)

        Returns:
            Dict with channel_name, channel_id, description, thumbnail, views, etc.

        Example:
            >>> info = toolkit.get_channel_info("@Fireship")
            >>> print(f"Channel: {info['channel_name']}")
            >>> print(f"Videos: {info['video_count']}")
        """
        return self._channel.get_channel_info(channel_url)

    def get_all_channel_videos(self, channel: str,
                               content_type: str = 'videos') -> List[Dict[str, Any]]:
        """
        Get ALL videos from a channel (unlimited) using scrapetube.

        This method requires scrapetube to be installed and can retrieve
        ALL videos from a channel without the 500 video limit of the API.

        Args:
            channel: Channel URL or identifier
            content_type: 'videos', 'shorts', or 'streams'

        Returns:
            List of all video info dicts

        Raises:
            ImportError: If scrapetube is not installed

        Example:
            >>> # Get ALL videos from a channel (may take time for large channels)
            >>> all_videos = toolkit.get_all_channel_videos("@Fireship")
            >>> print(f"Total videos: {len(all_videos)}")
        """
        return self._channel.get_all_channel_videos(channel, content_type)

    # =========================================================================
    # VIDEO CHAPTERS & ENGAGEMENT (v0.3+)
    # =========================================================================

    def get_video_chapters(self, url: str) -> List[Dict[str, Any]]:
        """
        Get video chapters/timestamps.

        Args:
            url: YouTube video URL

        Returns:
            List of chapter dicts with title, start_seconds, duration, formatted_start

        Example:
            >>> chapters = toolkit.get_video_chapters("https://youtube.com/watch?v=...")
            >>> for ch in chapters:
            ...     print(f"{ch['formatted_start']} - {ch['title']}")
        """
        return self._get_info.get_video_chapters(url)

    def get_key_moments(self, url: str) -> List[Dict[str, Any]]:
        """
        Get AI-generated key moments/timestamps.

        Args:
            url: YouTube video URL

        Returns:
            List of key moment dicts with title, start_seconds, duration
        """
        return self._get_info.get_key_moments(url)

    def get_replayed_heatmap(self, url: str) -> List[Dict[str, Any]]:
        """
        Get viewer engagement heatmap data (most replayed segments).

        Args:
            url: YouTube video URL

        Returns:
            List of heatmap segments with start_seconds, duration, intensity
        """
        return self._analyze.get_replayed_heatmap(url)

    # =========================================================================
    # ADVANCED SEARCH (PYTUBEFIX) (v0.3+)
    # =========================================================================

    def search_with_filters(self, query: str,
                            duration: Optional[str] = None,
                            upload_date: Optional[str] = None,
                            sort_by: Optional[str] = None,
                            features: Optional[List[str]] = None,
                            result_type: str = 'video',
                            max_results: int = 20) -> Dict[str, Any]:
        """
        Search YouTube with native filters (no API quota).

        This uses pytubefix's advanced search with YouTube's native filters.

        Args:
            query: Search query
            duration: 'short' (<4min), 'medium' (4-20min), 'long' (>20min)
            upload_date: 'hour', 'today', 'week', 'month', 'year'
            sort_by: 'relevance', 'date', 'views', 'rating'
            features: List of ['hd', '4k', 'live', 'cc', 'creative_commons', 'hdr', '360', 'vr180']
            result_type: 'video', 'channel', 'playlist'
            max_results: Max results to return

        Returns:
            Dict with videos, shorts, channels, playlists, completion_suggestions

        Example:
            >>> # Find medium-length Python tutorials from this month
            >>> results = toolkit.search_with_filters(
            ...     "python tutorial",
            ...     duration='medium',
            ...     upload_date='month',
            ...     sort_by='views'
            ... )
            >>> for video in results['videos']:
            ...     print(video['title'])
        """
        return self._search.search_with_filters(
            query, duration, upload_date, sort_by, features, result_type, max_results
        )

    # =========================================================================
    # PLAYLIST INFO (v0.3+)
    # =========================================================================

    def get_playlist_info(self, playlist_url: str) -> Dict[str, Any]:
        """
        Get comprehensive playlist information.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Dict with title, description, owner, views, video_count, etc.

        Example:
            >>> info = toolkit.get_playlist_info("https://youtube.com/playlist?list=...")
            >>> print(f"Playlist: {info['title']} ({info['video_count']} videos)")
        """
        return self._playlist.get_playlist_info(playlist_url)

    # =========================================================================
    # SCRAPETUBE SEARCH (v0.3+)
    # =========================================================================

    def search_without_api(self, query: str,
                           limit: int = 20,
                           sort_by: str = 'relevance') -> List[Dict[str, Any]]:
        """
        Search YouTube videos without using API quota.

        Uses scrapetube for search. Falls back to pytubefix if scrapetube
        is not installed.

        Args:
            query: Search query
            limit: Maximum results (default: 20)
            sort_by: 'relevance', 'upload_date', 'view_count', 'rating'

        Returns:
            List of video dicts

        Example:
            >>> results = toolkit.search_without_api("python tutorial", limit=10)
            >>> for video in results:
            ...     print(f"{video['title']} - {video['views']} views")
        """
        return self._search.search_without_api(query, limit, sort_by)

    # =========================================================================
    # NEW CLEAN API (v0.2+)
    # These methods provide a cleaner interface with proper return types.
    # The old methods above are kept for backward compatibility.
    # =========================================================================

    def get_video(self, url: str) -> VideoInfo:
        """
        Get video information as a VideoInfo object.

        This is the new clean API. Returns a proper dataclass instead of Dict.

        Args:
            url: YouTube video URL

        Returns:
            VideoInfo object with video details

        Raises:
            RuntimeError: If all extraction methods fail

        Example:
            >>> video = toolkit.get_video('https://youtube.com/watch?v=...')
            >>> print(video.title)
            >>> print(video.duration)
        """
        return self._get_info.get_video(url)

    def download(
        self,
        url: str,
        type: str = 'audio',
        format: str = 'wav',
        quality: str = 'best',
        output_path: Optional[str] = None,
        bitrate: str = '128k',
        progress: bool = True,
    ) -> DownloadResult:
        """
        Download media from YouTube as a DownloadResult object.

        This is the new clean API. Combines audio/video download into one method.

        Args:
            url: YouTube video URL
            type: 'audio' or 'video'
            format: For audio: 'wav', 'mp3', 'm4a'. For video: ignored (always mp4)
            quality: For video: 'best', '720p', '1080p', etc. For audio: ignored
            output_path: Custom output path (optional)
            bitrate: Audio bitrate: 'best', '320k', '256k', '192k', '128k'
            progress: Show download progress

        Returns:
            DownloadResult object with file path and metadata

        Example:
            >>> result = toolkit.download('https://youtube.com/watch?v=...', type='audio')
            >>> print(result.file_path)
            >>> print(result.success)

            >>> result = toolkit.download('https://youtube.com/watch?v=...', type='video', quality='720p')
            >>> if result.success:
            ...     print(f"Downloaded to {result.file_path}")
        """
        return self._download.download(url, type, format, quality, output_path, bitrate, progress)

    def search(
        self,
        query: str,
        max_results: int = 20,
        filters: Optional[SearchFilters] = None,
    ) -> SearchResult:
        """
        Search YouTube videos and return a SearchResult object.

        This is the new clean API. Returns proper dataclass instead of List[Dict].

        Args:
            query: Search query string
            max_results: Maximum number of results (default: 20)
            filters: Optional SearchFilters for advanced filtering

        Returns:
            SearchResult object containing search results

        Example:
            >>> results = toolkit.search('python tutorial', max_results=10)
            >>> for item in results.items:
            ...     print(item.title)

            >>> # With filters
            >>> from youtube_toolkit import SearchFilters
            >>> filters = SearchFilters(video_duration='short', order='viewCount')
            >>> results = toolkit.search('music', filters=filters)
        """
        return self._search.search(query, max_results, filters)

    def comments(
        self,
        url: str,
        max_results: int = 100,
        filters: Optional[CommentFilters] = None,
    ) -> CommentResult:
        """
        Get video comments as a CommentResult object.

        This is the new clean API. Returns proper dataclass instead of Dict/List.

        Args:
            url: YouTube video URL
            max_results: Maximum number of comments (default: 100)
            filters: Optional CommentFilters for advanced filtering

        Returns:
            CommentResult object containing comments and analytics

        Example:
            >>> result = toolkit.comments('https://youtube.com/watch?v=...')
            >>> print(f"Total comments: {result.total_results}")
            >>> for comment in result.comments:
            ...     print(f"{comment.author.display_name}: {comment.text}")

            >>> # With filters
            >>> from youtube_toolkit import CommentFilters, CommentOrder
            >>> filters = CommentFilters(order=CommentOrder.TIME, min_likes=10)
            >>> result = toolkit.comments(url, filters=filters)
        """
        return self._comments.comments(url, max_results, filters)

    def captions(
        self,
        url: str,
        language: str = 'en',
        filters: Optional[CaptionFilters] = None,
    ) -> CaptionResult:
        """
        Get available captions as a CaptionResult object.

        This is the new clean API. Returns proper dataclass instead of Dict.

        Args:
            url: YouTube video URL
            language: Preferred language code (default: 'en')
            filters: Optional CaptionFilters for advanced filtering

        Returns:
            CaptionResult object containing available caption tracks

        Example:
            >>> result = toolkit.captions('https://youtube.com/watch?v=...')
            >>> for track in result.tracks:
            ...     print(f"{track.language}: {track.name}")

            >>> # Get best track for English
            >>> best = result.get_best_track('en')
            >>> if best:
            ...     print(f"Best track: {best.name}")
        """
        return self._captions.captions(url, language, filters)

    def playlist(self, url: str) -> List[str]:
        """
        Get all video URLs from a playlist.

        This is the new clean API. Alias for get_playlist_urls.

        Args:
            url: YouTube playlist URL

        Returns:
            List of video URLs

        Example:
            >>> urls = toolkit.playlist('https://youtube.com/playlist?list=...')
            >>> print(f"Found {len(urls)} videos")
            >>> for video_url in urls:
            ...     video = toolkit.get_video(video_url)
            ...     print(video.title)
        """
        return self._playlist.playlist(url)

    # ==================== v0.5 FEATURES ====================

    # --- SponsorBlock Methods ---

    def get_sponsorblock_segments(self, url: str) -> List[Dict[str, Any]]:
        """
        Get SponsorBlock segments for a video.

        SponsorBlock is a crowdsourced database of sponsored segments, intros,
        outros, and other skippable content.

        Args:
            url: YouTube video URL

        Returns:
            List of segment dictionaries with category, start/end times, etc.
        """
        return self._analyze.get_sponsorblock_segments(url)

    def download_with_sponsorblock(self, url: str, output_path: str = None,
                                   action: str = 'remove',
                                   categories: List[str] = None) -> str:
        """
        Download video with SponsorBlock segments handled.

        Args:
            url: YouTube video URL
            output_path: Output directory
            action: 'remove' (cut out segments), 'mark' (add as chapters)
            categories: Categories to handle. Default: ['sponsor', 'selfpromo', 'intro', 'outro']

        Returns:
            Path to downloaded file
        """
        return self._download.download_with_sponsorblock(url, output_path, action, categories)

    # --- Live Stream Methods ---

    def get_live_status(self, url: str) -> Dict[str, Any]:
        """
        Get live stream status information.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with is_live, was_live, live_status, release_timestamp, etc.
        """
        return self._analyze.get_live_status(url)

    def download_live_stream(self, url: str, output_path: str = None,
                             from_start: bool = False,
                             duration: int = None) -> str:
        """
        Download a live stream or live stream archive.

        Args:
            url: YouTube live stream URL
            output_path: Output directory
            from_start: If True, download from the beginning of the stream
            duration: Maximum duration to download in seconds (None for full stream)

        Returns:
            Path to downloaded file
        """
        return self._download.download_live_stream(url, output_path, from_start, duration)

    def is_live(self, url: str) -> bool:
        """
        Check if a video is currently live streaming.

        Args:
            url: YouTube video URL

        Returns:
            True if currently live, False otherwise
        """
        return self._analyze.is_live(url)

    # --- Archive Methods ---

    def download_with_archive(self, url: str, output_path: str = None,
                              archive_file: str = None,
                              format: str = 'best') -> Optional[str]:
        """
        Download video with archive tracking to prevent re-downloads.

        Args:
            url: YouTube video URL
            output_path: Output directory
            archive_file: Path to archive file (default: 'downloaded.txt' in output_path)
            format: Format specification

        Returns:
            Path to downloaded file, or None if already in archive
        """
        return self._download.download_with_archive(url, output_path, archive_file, format)

    def is_in_archive(self, url: str, archive_file: str) -> bool:
        """
        Check if a video is already in the download archive.

        Args:
            url: YouTube video URL
            archive_file: Path to archive file

        Returns:
            True if video is in archive, False otherwise
        """
        return self._download.is_in_archive(url, archive_file)

    # --- Engagement Methods ---

    def get_heatmap(self, url: str) -> List[Dict[str, Any]]:
        """
        Get viewer engagement heatmap data (most replayed sections).

        Args:
            url: YouTube video URL

        Returns:
            List of heatmap segments with start_time, end_time, and value (intensity)
        """
        return self._analyze.get_heatmap(url)

    def get_comments_raw(self, url: str, max_comments: int = 100,
                         sort: str = 'top') -> List[Dict[str, Any]]:
        """
        Extract comments from a YouTube video using yt-dlp.

        Args:
            url: YouTube video URL
            max_comments: Maximum number of comments to retrieve
            sort: Sort order ('top' or 'new')

        Returns:
            List of comment dictionaries with author, text, likes, replies, etc.
        """
        return self._comments.get_comments_raw(url, max_comments, sort)

    # --- Cookies Methods ---

    def get_video_info_with_cookies(self, url: str, browser: str = 'chrome') -> Dict[str, Any]:
        """
        Get video info using cookies extracted from browser.
        Useful for age-restricted or member-only content.

        Args:
            url: YouTube video URL
            browser: Browser to extract cookies from ('chrome', 'firefox', 'safari', 'edge', etc.)

        Returns:
            Dictionary with video details
        """
        return self._get_info.get_video_info_with_cookies(url, browser)

    def get_supported_browsers(self) -> List[str]:
        """
        Get list of supported browsers for cookie extraction.

        Returns:
            List of supported browser names
        """
        return self._download.get_supported_browsers()

    # --- Subtitles Methods ---

    def download_subtitles(self, url: str, lang: str = 'en',
                           output_path: str = None) -> str:
        """
        Download subtitles for a video.

        Args:
            url: YouTube video URL
            lang: Language code
            output_path: Output path

        Returns:
            Path to subtitle file
        """
        return self._download.download_subtitles(url, lang, output_path)

    def convert_subtitles(self, input_path: str, output_format: str = 'srt') -> str:
        """
        Convert subtitle file to different format.

        Args:
            input_path: Path to input subtitle file
            output_format: Output format ('srt', 'vtt', 'ass', 'json3', 'ttml')

        Returns:
            Path to converted subtitle file
        """
        return self._download.convert_subtitles(input_path, output_format)

    def get_supported_subtitle_formats(self) -> List[str]:
        """
        Get supported subtitle formats for conversion.

        Returns:
            List of supported format names
        """
        return self._download.get_supported_subtitle_formats()

    # --- Chapters Methods ---

    def get_chapters(self, url: str) -> List[Dict[str, Any]]:
        """
        Get video chapters with automatic fallback.

        Args:
            url: YouTube video URL

        Returns:
            List of chapters with title, start_time, end_time, duration, formatted times
        """
        return self._get_info.get_chapters(url)

    def split_by_chapters(self, url: str, output_path: str = None,
                          format: str = 'mp4') -> List[str]:
        """
        Download and split video by chapters.

        Args:
            url: YouTube video URL
            output_path: Output directory
            format: Output format ('mp4', 'mp3', etc.)

        Returns:
            List of paths to split files
        """
        return self._download.split_by_chapters(url, output_path, format)

    # --- Thumbnail Methods ---

    def download_thumbnail(self, url: str, output_path: str = None,
                           quality: str = 'best') -> str:
        """
        Download video thumbnail.

        Args:
            url: YouTube video URL
            output_path: Output directory or file path
            quality: Thumbnail quality ('best', 'maxres', 'standard', 'high', 'medium', 'default')

        Returns:
            Path to downloaded thumbnail file
        """
        return self._download.download_thumbnail(url, output_path, quality)

    def get_thumbnail_url(self, url: str) -> str:
        """
        Get thumbnail URL without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Thumbnail URL
        """
        return self._get_info.get_thumbnail_url(url)

    # --- Enhanced Audio Methods ---

    def download_audio_with_metadata(self, url: str, output_path: str = None,
                                     format: str = 'mp3',
                                     embed_thumbnail: bool = True,
                                     add_metadata: bool = True) -> str:
        """
        Download audio with embedded metadata and thumbnail.

        Args:
            url: YouTube video URL
            output_path: Output directory
            format: Audio format ('mp3', 'm4a', 'opus', 'flac')
            embed_thumbnail: Whether to embed thumbnail in audio file
            add_metadata: Whether to add metadata tags

        Returns:
            Path to downloaded audio file
        """
        return self._download.download_audio_with_metadata(
            url, output_path, format, embed_thumbnail, add_metadata
        )

    # ==================== v0.6 FEATURES ====================

    # --- Match Filter Methods ---

    def download_with_filter(self, url: str, output_path: str = None,
                             match_filter: str = None,
                             format: str = 'best') -> Optional[str]:
        """
        Download video only if it matches the filter criteria.

        Filter expressions support:
        - Comparison operators: <, <=, >, >=, =, !=
        - Logical operators: & (and), | (or)
        - Fields: duration, view_count, like_count, upload_date, uploader, title, etc.

        Examples:
            - "duration > 600" - Videos longer than 10 minutes
            - "view_count > 10000" - Videos with more than 10k views
            - "duration > 300 & view_count > 1000" - Combined filter
            - "uploader = 'ChannelName'" - Specific channel
            - "upload_date >= 20240101" - Videos from 2024 onwards

        Args:
            url: YouTube video URL or playlist URL
            output_path: Output directory
            match_filter: Filter expression string
            format: Format specification

        Returns:
            Path to downloaded file, or None if filtered out
        """
        return self._download.download_with_filter(url, output_path, match_filter, format)

    def get_videos_matching_filter(self, url: str, match_filter: str = None,
                                   max_results: int = None) -> List[Dict[str, Any]]:
        """
        Get video info for videos matching the filter criteria (without downloading).

        Useful for previewing what would be downloaded before actually downloading.

        Args:
            url: YouTube video, playlist, or channel URL
            match_filter: Filter expression string
            max_results: Maximum number of results to return

        Returns:
            List of video info dictionaries that match the filter
        """
        return self._download.get_videos_matching_filter(url, match_filter, max_results)

    def filter_playlist(self, playlist_url: str, match_filter: str = None,
                        date_range: tuple = None,
                        min_views: int = None,
                        max_views: int = None,
                        min_duration: int = None,
                        max_duration: int = None,
                        title_contains: str = None,
                        title_not_contains: str = None) -> List[Dict[str, Any]]:
        """
        Filter playlist videos with convenient parameter options.

        This is a higher-level wrapper around match_filter for common use cases.

        Args:
            playlist_url: YouTube playlist URL
            match_filter: Raw filter expression (if provided, other params are ignored)
            date_range: Tuple of (start_date, end_date) in YYYYMMDD format
            min_views: Minimum view count
            max_views: Maximum view count
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            title_contains: Title must contain this string (case-insensitive)
            title_not_contains: Title must NOT contain this string

        Returns:
            List of matching video info dictionaries
        """
        return self._playlist.filter_playlist(
            playlist_url, match_filter, date_range,
            min_views, max_views, min_duration, max_duration,
            title_contains, title_not_contains
        )

    def batch_download_with_filter(self, url: str, output_path: str = None,
                                   match_filter: str = None,
                                   format: str = 'best',
                                   max_downloads: int = None,
                                   skip_existing: bool = True,
                                   concurrent_fragments: int = 1) -> List[str]:
        """
        Download multiple videos from playlist/channel with filter.

        Args:
            url: YouTube playlist or channel URL
            output_path: Output directory
            match_filter: Filter expression
            format: Format specification
            max_downloads: Maximum number of videos to download
            skip_existing: Skip videos that already exist in output_path
            concurrent_fragments: Per-video fragment parallelism (axis ①). Default
                1 = current behaviour. This is NOT multi-video parallelism: yt-dlp
                still iterates the batch sequentially so its filter semantics hold.

        Returns:
            List of paths to downloaded files
        """
        return self._download.batch_download_with_filter(
            url, output_path, match_filter, format, max_downloads, skip_existing,
            concurrent_fragments=concurrent_fragments
        )

    # --- Metadata File Export Methods ---

    def download_with_metadata_files(self, url: str, output_path: str = None,
                                     write_info_json: bool = True,
                                     write_description: bool = True,
                                     write_thumbnail: bool = True,
                                     write_subtitles: bool = False,
                                     subtitle_langs: List[str] = None,
                                     format: str = 'best') -> Dict[str, str]:
        """
        Download video with accompanying metadata files.

        Creates separate files for metadata, description, thumbnail, and subtitles.

        Args:
            url: YouTube video URL
            output_path: Output directory
            write_info_json: Create .info.json file with all metadata
            write_description: Create .description file
            write_thumbnail: Download thumbnail image
            write_subtitles: Download subtitle files
            subtitle_langs: List of subtitle languages (default: ['en'])
            format: Video format specification

        Returns:
            Dictionary mapping file types to their paths
        """
        return self._download.download_with_metadata_files(
            url, output_path, write_info_json, write_description,
            write_thumbnail, write_subtitles, subtitle_langs, format
        )

    def export_metadata_only(self, url: str, output_path: str = None,
                             format_type: str = 'json') -> str:
        """
        Export video metadata without downloading the video.

        Args:
            url: YouTube video URL
            output_path: Output file path or directory
            format_type: Output format ('json', 'description', 'all')

        Returns:
            Path to the exported metadata file
        """
        return self._download.export_metadata_only(url, output_path, format_type)

    def get_full_metadata(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata for a video (more fields than get_video_info).

        Includes all available fields from yt-dlp extraction: channel info,
        engagement metrics, thumbnails, categories, tags, live status,
        availability, format info, subtitles info, and more.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with comprehensive metadata (50+ fields)
        """
        return self._get_info.get_full_metadata(url)

    # --- YouTube Shorts Methods ---

    def is_youtube_short(self, url: str) -> bool:
        """
        Check if a URL is a YouTube Short.

        Args:
            url: YouTube URL

        Returns:
            True if the URL is a YouTube Short
        """
        return self._get_info.is_youtube_short(url)

    def get_shorts_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a YouTube Short.

        Args:
            url: YouTube Shorts URL

        Returns:
            Dictionary with Shorts-specific info (id, title, duration, is_short,
            view_count, like_count, uploader, thumbnail, etc.)
        """
        return self._get_info.get_shorts_info(url)

    def download_short(self, url: str, output_path: str = None,
                       format: str = 'mp4',
                       with_audio: bool = True) -> str:
        """
        Download a YouTube Short.

        Args:
            url: YouTube Shorts URL
            output_path: Output directory
            format: Output format ('mp4', 'webm')
            with_audio: Include audio in download

        Returns:
            Path to downloaded Short file
        """
        return self._download.download_short(url, output_path, format, with_audio)

    def get_channel_shorts(self, channel_url: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get all Shorts from a YouTube channel.

        Args:
            channel_url: YouTube channel URL
            max_results: Maximum number of Shorts to retrieve

        Returns:
            List of Shorts info dictionaries
        """
        return self._channel.get_channel_shorts(channel_url, max_results)

    def batch_download_shorts(self, channel_url: str, output_path: str = None,
                              max_downloads: int = 10,
                              format: str = 'mp4',
                              concurrent_fragments: int = 1) -> List[str]:
        """
        Download multiple Shorts from a channel.

        Args:
            channel_url: YouTube channel URL
            output_path: Output directory
            max_downloads: Maximum number of Shorts to download
            format: Output format
            concurrent_fragments: Per-Short fragment parallelism (axis ①). Default
                1 = current behaviour. Shorts are still downloaded one at a time.

        Returns:
            List of paths to downloaded files
        """
        return self._download.batch_download_shorts(
            channel_url, output_path, max_downloads, format,
            concurrent_fragments=concurrent_fragments
        )

    # ==================== v0.7 ANALYTICAL FEATURES ====================

    # --- Subscriptions API ---

    def get_channel_subscriptions(self, channel_id: str, max_results: int = 50,
                                  order: str = 'relevance',
                                  page_token: str = None) -> Dict[str, Any]:
        """
        Get subscriptions of a channel (channels they are subscribed to).

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results (max 50)
            order: Sort order ('alphabetical', 'relevance', 'unread')
            page_token: Token for pagination

        Returns:
            Dictionary with subscription data and pagination info
        """
        return self._channel.get_channel_subscriptions(channel_id, max_results, order, page_token)

    def check_subscription(self, channel_id: str, target_channel_id: str) -> Dict[str, Any]:
        """
        Check if a channel is subscribed to another channel.

        Args:
            channel_id: The channel to check subscriptions for
            target_channel_id: The channel to check if subscribed to

        Returns:
            Dictionary with subscription status and details
        """
        return self._channel.check_subscription(channel_id, target_channel_id)

    # --- Video Categories API ---

    def get_video_categories(self, region_code: str = 'US',
                            language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get video categories available in a region.

        Args:
            region_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'JP')
            language: Language for category names (e.g., 'en', 'es', 'ja')

        Returns:
            List of video category dictionaries with id, title, assignable
        """
        return self._search.get_video_categories(region_code, language)

    def get_category_by_id(self, category_id: str,
                          language: str = 'en') -> Dict[str, Any]:
        """
        Get a specific video category by ID.

        Args:
            category_id: Video category ID
            language: Language for category name

        Returns:
            Category dictionary or None if not found
        """
        return self._search.get_category_by_id(category_id, language)

    # --- i18n Languages/Regions API ---

    def get_supported_languages(self, language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of languages supported by YouTube.

        Args:
            language: Language for displaying names (e.g., 'en', 'es')

        Returns:
            List of supported language dictionaries with code and name
        """
        return self._system.get_supported_languages(language)

    def get_supported_regions(self, language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of regions/countries supported by YouTube.

        Args:
            language: Language for displaying names (e.g., 'en', 'es')

        Returns:
            List of supported region dictionaries with code and name
        """
        return self._system.get_supported_regions(language)

    # --- Activities API ---

    def get_channel_activities(self, channel_id: str, max_results: int = 25,
                              published_after: str = None,
                              published_before: str = None,
                              region_code: str = None,
                              page_token: str = None) -> Dict[str, Any]:
        """
        Get activity feed for a channel.

        Activity types include: upload, like, favorite, comment, subscription,
        playlistItem, recommendation, bulletin, channelItem, social, etc.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results (max 50)
            published_after: ISO 8601 datetime (e.g., '2024-01-01T00:00:00Z')
            published_before: ISO 8601 datetime
            region_code: Filter by region (e.g., 'US')
            page_token: Token for pagination

        Returns:
            Dictionary with activities and pagination info
        """
        return self._channel.get_channel_activities(
            channel_id, max_results, published_after, published_before, region_code, page_token
        )

    def get_recent_uploads(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent video uploads from a channel's activity feed.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of uploads to return

        Returns:
            List of recent upload dictionaries with video_id, title, url, etc.
        """
        return self._channel.get_recent_uploads(channel_id, max_results)

    # --- Trending/Popular Videos API ---

    def get_trending_videos(self, region_code: str = 'US',
                           category_id: str = None,
                           max_results: int = 25,
                           page_token: str = None) -> Dict[str, Any]:
        """
        Get trending/most popular videos in a region.

        Args:
            region_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'JP')
            category_id: Filter by video category ID (optional)
            max_results: Maximum number of results (max 50)
            page_token: Token for pagination

        Returns:
            Dictionary with trending videos and pagination info
        """
        return self._search.get_trending_videos(region_code, category_id, max_results, page_token)

    def get_trending_by_category(self, region_code: str = 'US',
                                 language: str = 'en') -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trending videos organized by category.

        Args:
            region_code: ISO 3166-1 alpha-2 country code
            language: Language for category names

        Returns:
            Dictionary mapping category names to lists of trending videos
        """
        return self._search.get_trending_by_category(region_code, language)

    # --- Channel Sections API ---

    def get_channel_sections(self, channel_id: str,
                            language: str = None) -> List[Dict[str, Any]]:
        """
        Get channel sections (shelves) that organize content on a channel page.

        Sections can include: uploads, playlists, featured channels, etc.

        Args:
            channel_id: YouTube channel ID
            language: Language for localized metadata

        Returns:
            List of channel section dictionaries
        """
        return self._channel.get_channel_sections(channel_id, language)

    def get_channel_featured_channels(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get featured channels from a channel's sections.

        Args:
            channel_id: YouTube channel ID

        Returns:
            List of featured channel IDs
        """
        return self._channel.get_channel_featured_channels(channel_id)

    # --- Enhanced Channel Info ---

    def get_channel_info_full(self, channel_id: str = None,
                              username: str = None,
                              handle: str = None) -> Dict[str, Any]:
        """
        Get comprehensive channel information.

        Provide ONE of: channel_id, username, or handle.

        Args:
            channel_id: YouTube channel ID (e.g., 'UC...')
            username: Legacy YouTube username
            handle: YouTube handle (e.g., '@MrBeast')

        Returns:
            Dictionary with comprehensive channel info including statistics,
            branding, topics, related playlists, and status
        """
        return self._channel.get_channel_info_full(channel_id, username, handle)

    def get_multiple_channels(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get information for multiple channels at once.

        Args:
            channel_ids: List of YouTube channel IDs (max 50)

        Returns:
            List of channel info dictionaries
        """
        return self._channel.get_multiple_channels(channel_ids)

    # =========================================================================
    # INTERNAL SINGLE-HANDLER DELEGATIONS
    # Thin wrappers used by the sub-API facade so it never touches handlers
    # directly. Each routes to exactly one handler call (no fallback) to keep
    # the facade's behavior unchanged. Not part of the public contract.
    # =========================================================================

    def get_video_info_pytubefix(self, url: str) -> Dict[str, Any]:
        """Get raw video info from pytubefix only (no fallback)."""
        return self._get_info.get_video_info_pytubefix(url)

    def get_available_formats_pytubefix(self, url: str) -> Dict[str, Any]:
        """Get available formats from pytubefix only (no fallback)."""
        return self._get_info.get_available_formats_pytubefix(url)

    def get_transcript(self, url: str) -> Any:
        """Get auto-generated transcript via yt-dlp."""
        return self._get_info.get_transcript(url)

    def get_lyrics(self, url: str) -> Any:
        """Get lyrics via yt-dlp."""
        return self._get_info.get_lyrics(url)

    def get_playlist_urls_pytubefix(self, url: str) -> List[str]:
        """Get playlist video URLs from pytubefix only (no fallback)."""
        return self._playlist.get_playlist_urls_pytubefix(url)

    def fetch_comment_replies(self, video_id: str, comment_id: str,
                              max_results: int = 50) -> List[Dict[str, Any]]:
        """Fetch replies to a comment via the YouTube API handler."""
        return self._comments.fetch_replies(video_id, comment_id, max_results=max_results)

    def extract_cookies_from_browser(self, browser: str = 'chrome') -> str:
        """Extract browser cookies to a file via yt-dlp."""
        return self._download.extract_cookies_from_browser(browser)

    def download_video_with_cookies(self, url: str, output_path: str = None,
                                    cookies: str = None) -> str:
        """Download a video via yt-dlp using a cookies file."""
        return self._download.download_video_with_cookies(url, output_path=output_path, cookies=cookies)

    def stream_to_buffer(self, url: str, stream_type: str = 'audio',
                         quality: str = 'best') -> bytes:
        """Stream content to an in-memory buffer via pytubefix."""
        return self._download.stream_to_buffer(url, stream_type, quality)

    def get_filesize_preview(self, url: str) -> Dict[str, Any]:
        """Get filesize preview for streams via pytubefix (no download)."""
        return self._download.get_filesize_preview(url)

    def search_videos_api(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search videos via the YouTube API handler only."""
        return self._search.search_videos_api(query, limit)

    def search_videos_pytubefix(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search videos via pytubefix only."""
        return self._search.search_videos_pytubefix(query, limit)

    def advanced_search_native(self, query: str, result_type: str = 'video',
                               limit: int = 20) -> Dict[str, Any]:
        """Run pytubefix native advanced search for a single result type."""
        return self._search.advanced_search_native(query, result_type=result_type, limit=limit)

    def get_search_suggestions(self, query: str) -> List[str]:
        """Get search autocomplete suggestions via pytubefix."""
        return self._search.get_search_suggestions(query)
