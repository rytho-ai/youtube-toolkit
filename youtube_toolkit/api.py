"""
api.py — YouTubeToolkit, the top-level entry point (★ load-bearing).

Wiring + public surface only. Owns the handlers (pytubefix / yt-dlp /
YouTube API) + anti-detection, constructs the domain services, and wires up
the five sub-APIs (get/download/search/analyze/stream) — which ARE the public
contract. The legacy flat methods are gone (see MIGRATION.md); business logic
and handler-fallback live in youtube_toolkit/services/, reached only through
the sub-APIs. Only two bare helpers stay here: extract_video_id (a util with
no sub-API home) and _sanitize_filename (used by the services).

Reads: handlers.* · services.* (domain logic) · sub_apis (5 facades) · utils.anti_detection
"""

from .handlers.pytubefix_handler import PyTubeFixHandler
from .handlers.yt_dlp_handler import YTDLPHandler
from .handlers.youtube_api_handler import YouTubeAPIHandler
from .utils.anti_detection import AntiDetectionManager
from .services.analyze import AnalyzeService
from .services.system import SystemService
from .services.channel import ChannelService
from .services.get_info import GetInfoService
from .services.playlist import PlaylistService
from .services.comments import CommentsService
from .services.captions import CaptionsService
from .services.search import SearchService
from .services.download import DownloadService


class YouTubeToolkit:
    """
    Main YouTube Toolkit class that combines multiple backends.

    This class orchestrates different handlers to provide robust
    YouTube functionality with automatic fallback.

    Consolidated API (v2.0) - Five Core Sub-APIs:
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

        # ANALYZE - Analyze content
        toolkit.analyze(url)                      # Full metadata
        toolkit.analyze.engagement(url)           # Heatmap + key moments
        toolkit.analyze.sponsorblock(url)         # Sponsor segments
        toolkit.analyze.filesize(url)             # Filesize preview

        # STREAM - Stream to buffer
        toolkit.stream(url)                       # Audio buffer
        toolkit.stream.audio(url)                 # Audio buffer
        toolkit.stream.video(url)                 # Video buffer
        toolkit.stream.live.status(url)           # Live stream status

    The legacy flat methods (toolkit.get_video_info(), etc.) were removed in
    v2.0; see MIGRATION.md for the flat-method -> sub-API mapping.
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
        # god class; the sub-APIs below delegate into these).
        self._analyze = AnalyzeService(self)
        self._system = SystemService(self)
        self._channel = ChannelService(self)
        self._get_info = GetInfoService(self)
        self._playlist = PlaylistService(self)
        self._comments = CommentsService(self)
        self._captions = CaptionsService(self)
        self._search = SearchService(self)
        self._download = DownloadService(self)

        # Initialize Core Sub-APIs (v2.0 Consolidated - 5 Core APIs)
        from .sub_apis import GetAPI, DownloadAPI, SearchAPI, AnalyzeAPI, StreamAPI
        self.get = GetAPI(self)
        self.download = DownloadAPI(self)
        self.search = SearchAPI(self)
        self.analyze = AnalyzeAPI(self)
        self.stream = StreamAPI(self)

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

    def _sanitize_filename(self, filename: str) -> str:
        """Convert filename to safe format for file system."""
        import re
        # Remove/replace invalid characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return safe_name[:100].strip()
