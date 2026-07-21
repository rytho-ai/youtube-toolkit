"""
services/ — domain service layer (business logic descended out of api.py).

Each module groups YouTubeToolkit's methods by domain (get_info, channel,
playlist, download, search, analyze, comments, captions, system, mine) so
api.py is a thin delegation layer. Every service takes a back-ref to the
toolkit and reads handlers through it (toolkit.pytubefix / .yt_dlp /
.youtube_api), keeping fallback orchestration and cross-domain calls routed
through api.py. `mine` is the one exception to "fallback orchestration" —
its OAuth-only calls have no other backend to fall back to.

Reads: youtube_toolkit.handlers.* (via toolkit back-ref), youtube_toolkit.core.*.
"""

from .get_info import GetInfoService
from .channel import ChannelService
from .playlist import PlaylistService
from .download import DownloadService
from .search import SearchService
from .analyze import AnalyzeService
from .comments import CommentsService
from .captions import CaptionsService
from .system import SystemService
from .mine import MineService

__all__ = [
    "GetInfoService",
    "ChannelService",
    "PlaylistService",
    "DownloadService",
    "SearchService",
    "AnalyzeService",
    "CommentsService",
    "CaptionsService",
    "SystemService",
    "MineService",
]
