"""
get_info.py — video info / metadata / chapters service.

Holds the video-information retrieval logic (info, formats, metadata, chapters,
shorts info, thumbnail url, cookie-based info) descended out of YouTubeToolkit
(api.py). api.py keeps one-line delegations; bodies are verbatim moves with
self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.core.video_info.VideoInfo.
"""

from typing import List, Dict, Any
from ..core.fallback import run_with_fallback
from ..core.video_info import VideoInfo


class GetInfoService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_video_info(self, url: str) -> Dict[str, Any]:
        # Try pytubefix first (usually most reliable), then fall back to yt-dlp.
        return run_with_fallback(
            [
                ("PyTubeFix", lambda: self._toolkit.pytubefix.get_video_info(url)),
                ("YT-DLP", lambda: self._toolkit.yt_dlp.get_video_info(url)),
            ],
            error_message="All video info extraction methods failed",
            verbose=self._toolkit.verbose,
        )

    def get_available_formats(self, url: str) -> Dict[str, Any]:
        # Try pytubefix first
        try:
            return self._toolkit.pytubefix.get_available_formats(url)
        except Exception as e:
            print(f"PyTubeFix formats failed: {e}")

        # Fallback to yt-dlp
        try:
            return self._toolkit.yt_dlp.get_available_formats(url)
        except Exception as e:
            print(f"YT-DLP formats failed: {e}")

        # If both fail, return empty dict
        return {}

    def get_video_description(self, url: str) -> str:
        return self._toolkit.yt_dlp.get_video_description(url)

    def get_rich_metadata(self, url: str) -> Dict[str, Any]:
        return self._toolkit.youtube_api.fetch_metadata(url)

    def get_video(self, url: str) -> VideoInfo:
        # Get raw dict from existing method
        data = self.get_video_info(url)

        # Convert to VideoInfo dataclass
        return VideoInfo(
            title=data.get('title', ''),
            duration=data.get('duration', 0),
            views=data.get('view_count', 0),
            author=data.get('channel', data.get('author', '')),
            video_id=data.get('video_id', ''),
            url=data.get('video_url', url),
            description=data.get('description'),
            thumbnail=data.get('thumbnail_url'),
            published_date=data.get('upload_date'),
            like_count=data.get('like_count'),
        )

    def get_full_metadata(self, url: str) -> Dict[str, Any]:
        return self._toolkit.yt_dlp.get_full_metadata(url)

    def is_youtube_short(self, url: str) -> bool:
        return self._toolkit.yt_dlp.is_youtube_short(url)

    def get_shorts_info(self, url: str) -> Dict[str, Any]:
        return self._toolkit.yt_dlp.get_shorts_info(url)

    def get_thumbnail_url(self, url: str) -> str:
        info = self._toolkit.yt_dlp.get_video_info(url)
        return info.get('thumbnail_url', '')

    def get_video_info_with_cookies(self, url: str, browser: str = 'chrome') -> Dict[str, Any]:
        return self._toolkit.yt_dlp.get_video_info_with_cookies_from_browser(url, browser)

    def get_video_chapters(self, url: str) -> List[Dict[str, Any]]:
        return self._toolkit.pytubefix.get_video_chapters(url)

    def get_chapters(self, url: str) -> List[Dict[str, Any]]:
        # Try pytubefix first
        try:
            result = self._toolkit.pytubefix.get_video_chapters(url)
            if result:
                return result
        except Exception:
            pass

        # Fallback to yt-dlp
        return self._toolkit.yt_dlp.get_chapters(url)

    def get_key_moments(self, url: str) -> List[Dict[str, Any]]:
        return self._toolkit.pytubefix.get_key_moments(url)

    def get_video_info_pytubefix(self, url: str) -> Dict[str, Any]:
        return self._toolkit.pytubefix.get_video_info(url)

    def get_available_formats_pytubefix(self, url: str) -> Dict[str, Any]:
        return self._toolkit.pytubefix.get_available_formats(url)

    def get_transcript(self, url: str) -> Any:
        return self._toolkit.ytdlp.get_transcript(url)

    def get_lyrics(self, url: str) -> Any:
        return self._toolkit.ytdlp.get_lyrics(url)
