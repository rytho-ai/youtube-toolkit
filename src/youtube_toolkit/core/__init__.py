"""
Core module for YouTube Toolkit.

This module contains the core data structures and post-processors used throughout the toolkit.
"""

from .video_info import VideoInfo
from .download import DownloadResult
from .search import SearchResult
from .post_processors import (
    BasePostProcessor,
    PyTubeFixPostProcessor,
    YTDLPPostProcessor,
    YouTubeAPIPostProcessor,
    PostProcessorFactory
)

__all__ = [
    "VideoInfo",
    "DownloadResult",
    "SearchResult",
    "BasePostProcessor",
    "PyTubeFixPostProcessor", 
    "YTDLPPostProcessor",
    "YouTubeAPIPostProcessor",
    "PostProcessorFactory"
]

# Version information
__version__ = "0.1.0"
