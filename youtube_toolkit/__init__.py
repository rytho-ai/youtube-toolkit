"""
YouTube Toolkit - A comprehensive YouTube information and download toolkit.

Install with: pip install youtube-toolkit
Usage: from youtube_toolkit import YouTubeToolkit

Version 2.0.0 - Consolidated API with 5 Core Sub-APIs:
    - GET: Retrieve information (video, channel, playlist, comments, chapters)
    - DOWNLOAD: Save content to disk (audio, video, captions, thumbnails)
    - SEARCH: Find content (videos, channels, playlists, trending)
    - ANALYZE: Analyze content (metadata, engagement, sponsorblock)
    - STREAM: Stream to buffer (audio, video, live streams)

Quick Start:
    from youtube_toolkit import YouTubeToolkit

    toolkit = YouTubeToolkit()

    # GET - Retrieve information
    video = toolkit.get(url)
    chapters = toolkit.get.chapters(url)
    channel_videos = toolkit.get.channel.videos("@Fireship")

    # DOWNLOAD - Save to disk
    result = toolkit.download(url, type='audio', format='mp3')
    toolkit.download.video(url, quality='720p')
    toolkit.download.with_sponsorblock(url)

    # SEARCH - Find content
    results = toolkit.search("python tutorial")
    trending = toolkit.search.trending()

    # ANALYZE - Analyze content
    metadata = toolkit.analyze.metadata(url)
    engagement = toolkit.analyze.engagement(url)
    segments = toolkit.analyze.sponsorblock(url)

    # STREAM - Stream to buffer
    audio_bytes = toolkit.stream.audio(url)
    is_live = toolkit.stream.live.is_live(url)
"""

from .api import YouTubeToolkit

__all__ = ["YouTubeToolkit"]
__version__ = "2.0.0"
__author__ = "Bo-Yu Chen"
__description__ = "A comprehensive YouTube information and download toolkit"

# Convenience imports for common use cases
from .core import VideoInfo, DownloadResult, SearchResult, PostProcessorFactory
from .core.search import SearchFilters, SearchResultItem, Thumbnails, Thumbnail, BooleanSearchQuery, YOUTUBE_CATEGORIES
from .core.comments import CommentFilters, CommentResult, Comment, CommentAuthor, CommentMetrics, CommentAnalytics, CommentSentimentAnalyzer, CommentOrder
from .core.captions import CaptionFilters, CaptionResult, CaptionTrack, CaptionContent, CaptionCue, CaptionAnalytics, CaptionFormatConverter, CaptionAnalyzer

# Make core classes available at package level for convenience
__all__.extend([
    "VideoInfo", "DownloadResult", "SearchResult", "PostProcessorFactory",
    "SearchFilters", "SearchResultItem", "Thumbnails", "Thumbnail",
    "BooleanSearchQuery", "YOUTUBE_CATEGORIES",
    "CommentFilters", "CommentResult", "Comment", "CommentAuthor",
    "CommentMetrics", "CommentAnalytics", "CommentSentimentAnalyzer", "CommentOrder",
    "CaptionFilters", "CaptionResult", "CaptionTrack", "CaptionContent",
    "CaptionCue", "CaptionAnalytics", "CaptionFormatConverter", "CaptionAnalyzer"
])
