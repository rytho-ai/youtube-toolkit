"""
Sub-API classes for action-based API design.

This module provides the five core action APIs (v1.0 consolidated):
- GetAPI: Retrieve information (video, channel, playlist, etc.)
- DownloadAPI: Save content to disk (audio, video, captions)
- SearchAPI: Find content (videos, channels, playlists)
- AnalyzeAPI: Analyze content (metadata, engagement, sponsorblock)
- StreamAPI: Stream content to buffer and manage live streams

Each sub-API is callable for smart defaults and has explicit methods for control.

The callable methods return the same types as the legacy API for backward compatibility:
- download() returns DownloadResult
- search() returns SearchResult
"""

from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
import os
import time

from .core.video_info import VideoInfo

if TYPE_CHECKING:
    from .api import YouTubeToolkit


# =============================================================================
# GET API - Retrieve information
# =============================================================================

class ChannelGetAPI:
    """Sub-API for channel-related get operations."""

    def __init__(self, parent: 'GetAPI'):
        self._parent = parent
        self._toolkit = parent._toolkit

    def __call__(self, channel: str) -> Dict[str, Any]:
        """
        Get channel information.

        Args:
            channel: Channel URL, handle (@name), or ID

        Returns:
            Channel metadata dict
        """
        return self._toolkit.get_channel_info(channel)

    def videos(self, channel: str,
               limit: Optional[int] = None,
               sort_by: str = 'newest',
               use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        """
        Get videos from a channel.

        Args:
            channel: Channel URL, handle, or ID
            limit: Maximum videos to return (None = all available)
            sort_by: 'newest', 'oldest', or 'popular'
            use_scrapetube: Use scrapetube for unlimited results

        Returns:
            List of video info dicts
        """
        if use_scrapetube:
            try:
                from .handlers.scrapetube_handler import ScrapeTubeHandler
                handler = ScrapeTubeHandler()
                return handler.get_channel_videos(channel, limit=limit, sort_by=sort_by)
            except ImportError:
                if self._toolkit.verbose:
                    print("⚠️ scrapetube not installed. Using pytubefix.")

        return self._toolkit.get_channel_videos(
            channel, content_type='videos', limit=limit, sort_by=sort_by
        )

    def shorts(self, channel: str,
               limit: Optional[int] = None,
               use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        """
        Get shorts from a channel.

        Args:
            channel: Channel URL, handle, or ID
            limit: Maximum shorts to return
            use_scrapetube: Use scrapetube for unlimited results

        Returns:
            List of shorts info dicts
        """
        if use_scrapetube:
            try:
                from .handlers.scrapetube_handler import ScrapeTubeHandler
                handler = ScrapeTubeHandler()
                return handler.get_channel_shorts(channel, limit=limit)
            except ImportError:
                if self._toolkit.verbose:
                    print("⚠️ scrapetube not installed. Using pytubefix.")

        return self._toolkit.get_channel_videos(
            channel, content_type='shorts', limit=limit
        )

    def streams(self, channel: str,
                limit: Optional[int] = None,
                use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        """
        Get live streams from a channel.

        Args:
            channel: Channel URL, handle, or ID
            limit: Maximum streams to return
            use_scrapetube: Use scrapetube for unlimited results

        Returns:
            List of stream info dicts
        """
        if use_scrapetube:
            try:
                from .handlers.scrapetube_handler import ScrapeTubeHandler
                handler = ScrapeTubeHandler()
                return handler.get_channel_streams(channel, limit=limit)
            except ImportError:
                if self._toolkit.verbose:
                    print("⚠️ scrapetube not installed. Using pytubefix.")

        return self._toolkit.get_channel_videos(
            channel, content_type='live', limit=limit
        )

    def all_videos(self, channel: str,
                   content_type: str = 'videos') -> List[Dict[str, Any]]:
        """
        Get ALL videos from a channel (unlimited) using scrapetube.

        Args:
            channel: Channel URL, handle, or ID
            content_type: 'videos', 'shorts', or 'streams'

        Returns:
            List of all video info dicts

        Raises:
            ImportError: If scrapetube is not installed
        """
        try:
            from .handlers.scrapetube_handler import ScrapeTubeHandler
            handler = ScrapeTubeHandler()

            if content_type == 'videos':
                return handler.get_channel_videos(channel, limit=None)
            elif content_type == 'shorts':
                return handler.get_channel_shorts(channel, limit=None)
            elif content_type == 'streams':
                return handler.get_channel_streams(channel, limit=None)
            else:
                raise ValueError(f"Invalid content_type: {content_type}")

        except ImportError:
            raise ImportError(
                "scrapetube is required for unlimited channel videos. "
                "Install with: pip install youtube-toolkit[scrapers]"
            )

    def playlists(self, channel: str,
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get playlists from a channel.

        Args:
            channel: Channel URL, handle, or ID
            limit: Maximum playlists to return

        Returns:
            List of playlist info dicts
        """
        return self._toolkit.get_channel_videos(
            channel, content_type='playlists', limit=limit
        )


class PlaylistGetAPI:
    """Sub-API for playlist-related get operations."""

    def __init__(self, parent: 'GetAPI'):
        self._parent = parent
        self._toolkit = parent._toolkit

    def __call__(self, url: str) -> Dict[str, Any]:
        """
        Get playlist information.

        Args:
            url: Playlist URL

        Returns:
            Playlist metadata dict
        """
        return self._toolkit.get_playlist_info(url)

    def urls(self, url: str) -> List[str]:
        """
        Get all video URLs from a playlist.

        Args:
            url: Playlist URL

        Returns:
            List of video URLs
        """
        return self._toolkit.get_playlist_urls_pytubefix(url)

    def videos(self, url: str,
               limit: Optional[int] = None,
               use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        """
        Get video details from a playlist.

        Args:
            url: Playlist URL
            limit: Maximum videos to return
            use_scrapetube: Use scrapetube for scraping

        Returns:
            List of video info dicts
        """
        if use_scrapetube:
            try:
                from .handlers.scrapetube_handler import ScrapeTubeHandler
                handler = ScrapeTubeHandler()
                return handler.get_playlist_videos(url, limit=limit)
            except ImportError:
                if self._toolkit.verbose:
                    print("⚠️ scrapetube not installed. Getting URLs only.")

        # Fallback: get URLs and fetch info for each
        urls = self.urls(url)
        if limit:
            urls = urls[:limit]
        return urls  # Return URLs, user can fetch details if needed


class CommentsGetAPI:
    """Sub-API for comments-related get operations."""

    def __init__(self, parent: 'GetAPI'):
        self._parent = parent
        self._toolkit = parent._toolkit

    def __call__(self, url: str,
                 limit: int = 100,
                 order: str = 'relevance') -> Dict[str, Any]:
        """
        Get comments from a video.

        Args:
            url: Video URL
            limit: Maximum comments to return
            order: 'relevance' or 'time'

        Returns:
            CommentResult with comments and analytics
        """
        from .core.comments import CommentFilters, CommentOrder

        order_enum = CommentOrder.RELEVANCE if order == 'relevance' else CommentOrder.TIME
        filters = CommentFilters(order=order_enum, max_results=limit)

        return self._toolkit.comments(url, filters=filters)

    def replies(self, url: str, comment_id: str,
                limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get replies to a comment.

        Args:
            url: Video URL
            comment_id: Parent comment ID
            limit: Maximum replies to return

        Returns:
            List of reply dicts
        """
        return self._toolkit.fetch_comment_replies(
            self._toolkit.extract_video_id(url),
            comment_id,
            max_results=limit
        )

    def search(self, url: str, query: str,
               limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search within video comments.

        Args:
            url: Video URL
            query: Search query
            limit: Maximum results

        Returns:
            List of matching comments
        """
        from .core.comments import CommentFilters

        filters = CommentFilters(search_terms=[query], max_results=limit)
        result = self._toolkit.comments(url, filters=filters)
        return result.comments if hasattr(result, 'comments') else []


class GetAPI:
    """
    GET API - Retrieve information from YouTube.

    Usage:
        toolkit.get(url)                    # Smart auto-detect
        toolkit.get.video(url)              # Explicit video info
        toolkit.get.channel("@Fireship")    # Channel info
        toolkit.get.channel.videos(...)     # Channel videos
        toolkit.get.playlist(url)           # Playlist info
        toolkit.get.chapters(url)           # Video chapters
        toolkit.get.transcript(url)         # Video transcript
        toolkit.get.comments(url)           # Video comments
        toolkit.get.captions(url)           # Caption tracks
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit
        self.channel = ChannelGetAPI(self)
        self.playlist = PlaylistGetAPI(self)
        self.comments = CommentsGetAPI(self)

    def __call__(self, url: str,
                 include: Optional[List[str]] = None) -> Union[VideoInfo, Dict[str, Any]]:
        """
        Smart get - auto-detect URL type and return appropriate info.

        Args:
            url: YouTube URL (video, channel, or playlist)
            include: Extra data to include (for videos):
                     ['chapters', 'heatmap', 'key_moments', 'transcript']

        Returns:
            VideoInfo for videos, dict for channels/playlists
        """
        # Detect URL type
        url_lower = url.lower()

        if '/playlist' in url_lower or 'list=' in url_lower:
            return self.playlist(url)
        elif '/@' in url_lower or '/channel/' in url_lower or '/c/' in url_lower:
            return self.channel(url)
        elif url.startswith('@'):
            return self.channel(url)
        else:
            return self.video(url, include=include)

    def video(self, url: str,
              include: Optional[List[str]] = None) -> VideoInfo:
        """
        Get video information.

        Args:
            url: Video URL
            include: Extra data to include:
                     ['chapters', 'heatmap', 'key_moments', 'transcript', 'lyrics']

        Returns:
            VideoInfo dataclass with video details
        """
        # Get base info from handler
        info = self._toolkit.get_video_info_pytubefix(url)

        # Map handler dict keys to VideoInfo fields
        video_info = VideoInfo(
            title=info.get('title', ''),
            duration=info.get('duration', 0),
            views=info.get('view_count', 0),
            author=info.get('channel', ''),
            video_id=info.get('video_id', ''),
            url=info.get('video_url', url),
            description=info.get('description'),
            thumbnail=info.get('thumbnail_url'),
            published_date=info.get('upload_date'),
            like_count=info.get('like_count'),
        )

        # Add extras if requested (stored as additional attributes)
        if include:
            if 'chapters' in include:
                try:
                    video_info.chapters = self._toolkit.get_video_chapters(url)
                except Exception:
                    video_info.chapters = []

            if 'heatmap' in include:
                try:
                    video_info.heatmap = self._toolkit.get_replayed_heatmap(url)
                except Exception:
                    video_info.heatmap = []

            if 'key_moments' in include:
                try:
                    video_info.key_moments = self._toolkit.get_key_moments(url)
                except Exception:
                    video_info.key_moments = []

            if 'transcript' in include:
                try:
                    video_info.transcript = self._toolkit.get_transcript(url)
                except Exception:
                    video_info.transcript = None

            if 'lyrics' in include:
                try:
                    video_info.lyrics = self._toolkit.get_lyrics(url)
                except Exception:
                    video_info.lyrics = None

        return video_info

    def chapters(self, url: str) -> List[Dict[str, Any]]:
        """
        Get video chapters/timestamps.

        Args:
            url: Video URL

        Returns:
            List of chapter dicts with title, start_seconds, formatted_start
        """
        return self._toolkit.get_video_chapters(url)

    def key_moments(self, url: str) -> List[Dict[str, Any]]:
        """
        Get AI-generated key moments.

        Args:
            url: Video URL

        Returns:
            List of key moment dicts
        """
        return self._toolkit.get_key_moments(url)

    def heatmap(self, url: str) -> List[Dict[str, Any]]:
        """
        Get viewer engagement heatmap (most replayed sections).

        Args:
            url: Video URL

        Returns:
            List of heatmap segments with intensity
        """
        return self._toolkit.get_replayed_heatmap(url)

    def transcript(self, url: str, lang: str = 'en') -> Optional[str]:
        """
        Get auto-generated transcript.

        Args:
            url: Video URL
            lang: Language code

        Returns:
            Transcript text or None
        """
        return self._toolkit.get_transcript(url)

    def lyrics(self, url: str) -> Optional[str]:
        """
        Get lyrics from video (if available in description/metadata).

        Args:
            url: Video URL

        Returns:
            Lyrics text or None
        """
        return self._toolkit.get_lyrics(url)

    def captions(self, url: str) -> Dict[str, Any]:
        """
        Get available caption tracks.

        Args:
            url: Video URL

        Returns:
            CaptionResult with available tracks
        """
        return self._toolkit.captions(url)

    def metadata(self, url: str) -> Dict[str, Any]:
        """
        Get extended metadata via YouTube API.

        Args:
            url: Video URL

        Returns:
            Rich metadata dict
        """
        return self._toolkit.get_rich_metadata(url)

    def keywords(self, url: str) -> List[str]:
        """
        Get video keywords/tags.

        Args:
            url: Video URL

        Returns:
            List of keywords/tags
        """
        info = self._toolkit.get_video_info_pytubefix(url)
        return info.get('keywords', []) or []

    def formats(self, url: str) -> Dict[str, Any]:
        """
        Get available download formats for a video.

        Args:
            url: Video URL

        Returns:
            Dict with audio and video format options
        """
        return self._toolkit.get_available_formats_pytubefix(url)

    def restriction(self, url: str) -> Dict[str, Any]:
        """
        Get video restriction/availability info.

        Args:
            url: Video URL

        Returns:
            Dict with age_restricted, is_private, is_unlisted, etc.
        """
        try:
            info = self._toolkit.get_full_metadata(url)
            return {
                'age_restricted': info.get('age_limit', 0) > 0,
                'age_limit': info.get('age_limit', 0),
                'is_private': info.get('is_private', False),
                'is_unlisted': info.get('is_unlisted', False),
                'availability': info.get('availability', 'public'),
                'live_status': info.get('live_status'),
                'playable_in_embed': info.get('playable_in_embed', True),
            }
        except Exception:
            return {'age_restricted': False, 'availability': 'unknown'}

    def embed_url(self, url: str) -> str:
        """
        Get embeddable URL for a video.

        Args:
            url: Video URL

        Returns:
            Embed URL string
        """
        video_id = self._toolkit.extract_video_id(url)
        return f"https://www.youtube.com/embed/{video_id}"


# =============================================================================
# DOWNLOAD API - Save content to disk
# =============================================================================

class DownloadAPI:
    """
    DOWNLOAD API - Save YouTube content to disk.

    Usage:
        toolkit.download(url)                           # Audio (default) -> DownloadResult
        toolkit.download.audio(url, format='mp3')       # Explicit audio -> str (path)
        toolkit.download.video(url, quality='1080p')    # Video -> str (path)
        toolkit.download.captions(url, lang='en')       # Captions -> str (path)
        toolkit.download.thumbnail(url)                 # Thumbnail image -> str (path)
        toolkit.download.playlist(url, type='audio')    # Batch download -> Dict
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit

    def __call__(self, url: str,
                 type: str = 'audio',
                 format: str = 'wav',
                 quality: str = 'best',
                 output_path: Optional[str] = None,
                 bitrate: str = '128k',
                 progress: bool = True,
                 **kwargs):
        """
        Smart download - returns DownloadResult for backward compatibility.

        Args:
            url: Video URL
            type: 'audio' or 'video'
            format: For audio: 'wav', 'mp3', 'm4a'. For video: ignored
            quality: For video: 'best', '720p', '1080p', etc.
            output_path: Output directory or file path
            bitrate: Audio bitrate: 'best', '320k', '256k', '192k', '128k'
            progress: Show download progress

        Returns:
            DownloadResult object with file path and metadata
        """
        from .core.download import DownloadResult

        start_time = time.time()
        backend_used = None

        try:
            if type == 'audio':
                file_path = self.audio(
                    url,
                    format=format,
                    output_path=output_path,
                    bitrate=bitrate,
                    progress_callback=progress,
                )
                backend_used = 'pytubefix/yt-dlp'
                result_format = format
                result_quality = bitrate
            elif type == 'video':
                file_path = self.video(
                    url,
                    quality=quality,
                    output_path=output_path,
                    progress_callback=progress,
                )
                backend_used = 'yt-dlp/pytubefix'
                result_format = 'mp4'
                result_quality = quality
            else:
                raise ValueError(f"Invalid type: {type}. Must be 'audio' or 'video'")

            download_time = time.time() - start_time

            # Get file size if file exists
            file_size = None
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)

            return DownloadResult(
                file_path=file_path,
                success=True,
                file_size=file_size,
                download_time=download_time,
                format=result_format,
                quality=result_quality,
                backend_used=backend_used,
            )

        except Exception as e:
            download_time = time.time() - start_time
            return DownloadResult(
                file_path=output_path or '',
                success=False,
                error_message=str(e),
                download_time=download_time,
                backend_used=backend_used,
            )

    def audio(self, url: str,
              format: str = 'mp3',
              output_path: Optional[str] = None,
              bitrate: str = 'best',
              prefer_yt_dlp: bool = False,
              progress_callback: bool = True) -> str:
        """
        Download audio from a video.

        Args:
            url: Video URL
            format: Output format ('mp3', 'wav', 'm4a')
            output_path: Output directory or file path
            bitrate: Audio bitrate ('best', '320k', '256k', '192k', '128k')
            prefer_yt_dlp: Use yt-dlp instead of pytubefix
            progress_callback: Show download progress

        Returns:
            Path to downloaded audio file
        """
        return self._toolkit.download_audio(
            url,
            format=format,
            output_path=output_path,
            bitrate=bitrate,
            prefer_yt_dlp=prefer_yt_dlp,
            progress_callback=progress_callback
        )

    def video(self, url: str,
              quality: str = 'best',
              output_path: Optional[str] = None,
              prefer_yt_dlp: bool = False,
              progress_callback: bool = True) -> str:
        """
        Download video.

        Args:
            url: Video URL
            quality: Video quality ('best', '1080p', '720p', '480p', '360p')
            output_path: Output directory or file path
            prefer_yt_dlp: Use yt-dlp instead of pytubefix
            progress_callback: Show download progress

        Returns:
            Path to downloaded video file
        """
        return self._toolkit.download_video(
            url,
            quality=quality,
            output_path=output_path,
            prefer_yt_dlp=prefer_yt_dlp,
            progress_callback=progress_callback
        )

    def captions(self, url: str,
                 lang: str = 'en',
                 format: str = 'srt',
                 output_path: Optional[str] = None) -> str:
        """
        Download captions/subtitles.

        Args:
            url: Video URL
            lang: Language code ('en', 'es', 'ja', etc.)
            format: Caption format ('srt', 'vtt', 'txt', 'json')
            output_path: Output directory or file path

        Returns:
            Path to downloaded caption file
        """
        return self._toolkit.download_captions(
            url,
            lang=lang,
            format=format,
            output_path=output_path
        )

    def thumbnail(self, url: str,
                  output_path: Optional[str] = None,
                  quality: str = 'maxres') -> str:
        """
        Download video thumbnail.

        Args:
            url: Video URL
            output_path: Output directory or file path
            quality: Thumbnail quality ('maxres', 'high', 'medium', 'default')

        Returns:
            Path to downloaded thumbnail
        """
        import requests
        import os

        video_id = self._toolkit.extract_video_id(url)

        # Thumbnail URL patterns by quality
        quality_urls = {
            'maxres': f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',
            'high': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
            'medium': f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
            'default': f'https://i.ytimg.com/vi/{video_id}/default.jpg',
        }

        thumb_url = quality_urls.get(quality, quality_urls['high'])

        # Try to get thumbnail, fallback to lower quality if not available
        response = requests.get(thumb_url)
        if response.status_code != 200 and quality == 'maxres':
            thumb_url = quality_urls['high']
            response = requests.get(thumb_url)

        if response.status_code != 200:
            raise RuntimeError(f"Failed to download thumbnail: {response.status_code}")

        # Determine output path
        if output_path is None:
            output_path = f'{video_id}_thumbnail.jpg'
        elif os.path.isdir(output_path):
            output_path = os.path.join(output_path, f'{video_id}_thumbnail.jpg')

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path

    def playlist(self, url: str,
                 type: str = 'audio',
                 format: str = 'mp3',
                 output_path: Optional[str] = None,
                 **kwargs) -> Dict[str, Any]:
        """
        Download all videos from a playlist.

        Args:
            url: Playlist URL
            type: 'audio' or 'video'
            format: Output format
            output_path: Output directory
            **kwargs: Additional options

        Returns:
            Dict with download results and summary
        """
        return self._toolkit.download_playlist_media(
            url,
            media_type=type,
            format=format,
            output_path=output_path,
            **kwargs
        )

    def shorts(self, url: str,
               output_path: Optional[str] = None,
               format: str = 'mp4',
               with_audio: bool = True) -> str:
        """
        Download a YouTube Short.

        Args:
            url: YouTube Shorts URL
            output_path: Output directory
            format: Output format ('mp4', 'webm')
            with_audio: Include audio

        Returns:
            Path to downloaded file
        """
        return self._toolkit.download_short(url, output_path, format, with_audio)

    def live(self, url: str,
             output_path: Optional[str] = None,
             from_start: bool = False,
             duration: Optional[int] = None) -> str:
        """
        Download a live stream.

        Args:
            url: YouTube live stream URL
            output_path: Output directory
            from_start: Download from beginning of stream
            duration: Max duration in seconds

        Returns:
            Path to downloaded file
        """
        return self._toolkit.download_live_stream(url, output_path, from_start, duration)

    def with_sponsorblock(self, url: str,
                          output_path: Optional[str] = None,
                          action: str = 'remove',
                          categories: Optional[List[str]] = None) -> str:
        """
        Download video with SponsorBlock segments handled.

        Args:
            url: YouTube video URL
            output_path: Output directory
            action: 'remove' (cut out), 'mark' (add as chapters)
            categories: Categories to handle. Default: ['sponsor', 'selfpromo', 'intro', 'outro']

        Returns:
            Path to downloaded file
        """
        return self._toolkit.download_with_sponsorblock(url, output_path, action, categories)

    def with_metadata(self, url: str,
                      output_path: Optional[str] = None,
                      format: str = 'mp3',
                      embed_thumbnail: bool = True,
                      add_metadata: bool = True) -> str:
        """
        Download audio with embedded metadata and thumbnail.

        Args:
            url: YouTube video URL
            output_path: Output directory
            format: 'mp3', 'm4a', 'opus', 'flac'
            embed_thumbnail: Embed cover art
            add_metadata: Add ID3/metadata tags

        Returns:
            Path to audio file
        """
        return self._toolkit.download_audio_with_metadata(
            url, output_path, format, embed_thumbnail, add_metadata
        )

    def with_filter(self, url: str,
                    output_path: Optional[str] = None,
                    match_filter: Optional[str] = None,
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

        Args:
            url: YouTube video URL or playlist URL
            output_path: Output directory
            match_filter: Filter expression string
            format: Format specification

        Returns:
            Path to downloaded file, or None if filtered out
        """
        return self._toolkit.download_with_filter(url, output_path, match_filter, format)

    def with_archive(self, url: str,
                     output_path: Optional[str] = None,
                     archive_file: Optional[str] = None,
                     format: str = 'best') -> Optional[str]:
        """
        Download with archive tracking (skip already downloaded).

        Args:
            url: YouTube video URL
            output_path: Output directory
            archive_file: Path to archive file
            format: Format specification

        Returns:
            Path to file, or None if already in archive
        """
        return self._toolkit.download_with_archive(url, output_path, archive_file, format)

    def with_cookies(self, url: str,
                     browser: str = 'chrome',
                     output_path: Optional[str] = None,
                     format: str = 'best') -> str:
        """
        Download using browser cookies for authentication.
        Useful for age-restricted or member-only content.

        Args:
            url: YouTube video URL
            browser: 'chrome', 'firefox', 'safari', 'edge', 'brave', etc.
            output_path: Output directory
            format: Format specification

        Returns:
            Path to downloaded file
        """
        # Extract cookies and use them for download
        cookies_file = self._toolkit.extract_cookies_from_browser(browser)
        return self._toolkit.download_video_with_cookies(
            url, output_path=output_path, cookies=cookies_file
        )


# =============================================================================
# SEARCH API - Find content
# =============================================================================

class SearchAPI:
    """
    SEARCH API - Find YouTube content.

    Usage:
        toolkit.search("query")                         # Videos (default) -> SearchResult
        toolkit.search.videos("query", limit=20)        # Explicit videos -> List[Dict]
        toolkit.search.channels("query")                # Channels -> List[Dict]
        toolkit.search.playlists("query")               # Playlists -> List[Dict]
        toolkit.search.with_filters("query", ...)       # Advanced filters -> Dict
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit

    def __call__(self, query: str,
                 max_results: int = 20,
                 filters=None):
        """
        Smart search - returns SearchResult for backward compatibility.

        Args:
            query: Search query
            max_results: Maximum number of results (default: 20)
            filters: Optional SearchFilters for advanced filtering

        Returns:
            SearchResult object containing search results
        """
        from .core.search import SearchResult, SearchFilters, SearchResultItem

        if filters is None:
            filters = SearchFilters()

        filters.max_results = max_results

        # Use existing advanced_search which returns dict
        raw_result = self._toolkit.advanced_search(query, filters, max_results)

        # Convert to SearchResult
        items = []
        raw_items = raw_result.get('items', [])

        for item in raw_items:
            if isinstance(item, SearchResultItem):
                items.append(item)
            elif isinstance(item, dict):
                items.append(SearchResultItem(
                    kind=item.get('kind', 'youtube#video'),
                    etag=item.get('etag', ''),
                    video_id=item.get('video_id', item.get('id', {}).get('videoId', '')),
                    title=item.get('title', item.get('snippet', {}).get('title', '')),
                    description=item.get('description', item.get('snippet', {}).get('description', '')),
                    channel_title=item.get('channel_title', item.get('snippet', {}).get('channelTitle', '')),
                ))

        return SearchResult(
            items=items,
            total_results=raw_result.get('pageInfo', {}).get('totalResults', len(items)),
            query=query,
            filters_applied=filters,
            next_page_token=raw_result.get('nextPageToken'),
            prev_page_token=raw_result.get('prevPageToken'),
        )

    def videos(self, query: str,
               limit: int = 20,
               use_api: bool = False) -> List[Dict[str, Any]]:
        """
        Search for videos.

        Args:
            query: Search query
            limit: Maximum results
            use_api: Use YouTube API (requires API key, uses quota)

        Returns:
            List of video results
        """
        if use_api:
            return self._toolkit.search_videos_api(query, limit)

        # Try pytubefix first, then scrapetube
        try:
            results = self._toolkit.search_videos_pytubefix(query, limit)
            if results:
                return results
        except Exception:
            pass

        # Fallback to scrapetube
        try:
            from .handlers.scrapetube_handler import ScrapeTubeHandler
            handler = ScrapeTubeHandler()
            return handler.search(query, limit=limit)
        except ImportError:
            pass

        return []

    def channels(self, query: str,
                 limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for channels.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of channel results
        """
        results = self._toolkit.advanced_search_native(
            query, result_type='channel', limit=limit
        )
        return results.get('channels', [])

    def playlists(self, query: str,
                  limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for playlists.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of playlist results
        """
        results = self._toolkit.advanced_search_native(
            query, result_type='playlist', limit=limit
        )
        return results.get('playlists', [])

    def with_filters(self, query: str,
                     duration: Optional[str] = None,
                     upload_date: Optional[str] = None,
                     sort_by: Optional[str] = None,
                     features: Optional[List[str]] = None,
                     result_type: str = 'video',
                     max_results: int = 20) -> Dict[str, Any]:
        """
        Search with advanced filters (no API quota).

        Args:
            query: Search query
            duration: 'short' (<4min), 'medium' (4-20min), 'long' (>20min)
            upload_date: 'hour', 'today', 'week', 'month', 'year'
            sort_by: 'relevance', 'date', 'views', 'rating'
            features: ['hd', '4k', 'live', 'cc', 'creative_commons', 'hdr']
            result_type: 'video', 'channel', 'playlist'
            max_results: Maximum results

        Returns:
            Dict with videos, shorts, channels, playlists, completion_suggestions
        """
        return self._toolkit.search_with_filters(
            query=query,
            duration=duration,
            upload_date=upload_date,
            sort_by=sort_by,
            features=features,
            result_type=result_type,
            max_results=max_results
        )

    def suggestions(self, query: str) -> List[str]:
        """
        Get search autocomplete suggestions.

        Args:
            query: Partial search query

        Returns:
            List of suggested queries
        """
        return self._toolkit.get_search_suggestions(query)

    @property
    def trending(self) -> 'TrendingSearchAPI':
        """Access trending search functionality."""
        if not hasattr(self, '_trending'):
            self._trending = TrendingSearchAPI(self._toolkit)
        return self._trending

    def categories(self, region: str = 'US', language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get video categories available in a region.

        Args:
            region: ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'JP')
            language: Language for category names

        Returns:
            List of category dictionaries with id, title, assignable
        """
        return self._toolkit.get_video_categories(region, language)

    def regions(self, display_language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of regions/countries supported by YouTube.

        Args:
            display_language: Language for displaying names

        Returns:
            List of region dictionaries with code and name
        """
        return self._toolkit.get_supported_regions(display_language)

    def languages(self, display_language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of languages supported by YouTube.

        Args:
            display_language: Language for displaying names

        Returns:
            List of language dictionaries with code and name
        """
        return self._toolkit.get_supported_languages(display_language)


class TrendingSearchAPI:
    """
    Trending Videos API - Discover popular content.

    Usage:
        videos = toolkit.search.trending()
        videos = toolkit.search.trending.by_category(region='US')
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit

    def __call__(self, region: str = 'US', category: Optional[str] = None,
                 max_results: int = 25) -> Dict[str, Any]:
        """
        Get trending/most popular videos in a region.

        Args:
            region: ISO 3166-1 alpha-2 country code
            category: Filter by video category ID
            max_results: Maximum results (max 50)

        Returns:
            Dictionary with trending videos
        """
        return self._toolkit.get_trending_videos(region, category, max_results)

    def by_category(self, region: str = 'US',
                    language: str = 'en') -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trending videos organized by category.

        Args:
            region: ISO 3166-1 alpha-2 country code
            language: Language for category names

        Returns:
            Dictionary mapping category names to trending videos
        """
        return self._toolkit.get_trending_by_category(region, language)


# =============================================================================
# ANALYZE API - Analyze content (NEW in v1.0)
# =============================================================================

class AnalyzeAPI:
    """
    ANALYZE API - Analyze YouTube content.

    Usage:
        toolkit.analyze(url)                    # Full metadata analysis
        toolkit.analyze.metadata(url)           # Extended metadata
        toolkit.analyze.engagement(url)         # Heatmap and key moments
        toolkit.analyze.comments(url)           # Comment analytics
        toolkit.analyze.captions(url)           # Caption analysis
        toolkit.analyze.sponsorblock(url)       # SponsorBlock segments
        toolkit.analyze.channel(channel)        # Channel analytics
        toolkit.analyze.filesize(url)           # Filesize preview
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit

    def __call__(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive analysis of a video.

        Args:
            url: Video URL

        Returns:
            Dict with full metadata, engagement data, and more
        """
        return self.metadata(url)

    def metadata(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata (50+ fields).

        Includes: channel info, engagement metrics, thumbnails, categories,
        tags, live status, availability, format info, subtitles info, and more.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with comprehensive metadata
        """
        return self._toolkit.get_full_metadata(url)

    def engagement(self, url: str) -> Dict[str, Any]:
        """
        Get viewer engagement data (heatmap and key moments).

        Args:
            url: YouTube video URL

        Returns:
            Dict with heatmap and key_moments data
        """
        result = {}
        try:
            result['heatmap'] = self._toolkit.get_replayed_heatmap(url)
        except Exception:
            result['heatmap'] = []

        try:
            result['key_moments'] = self._toolkit.get_key_moments(url)
        except Exception:
            result['key_moments'] = []

        return result

    def comments(self, url: str, max_comments: int = 100,
                 sort: str = 'relevance') -> Dict[str, Any]:
        """
        Get video comments with analytics.

        Args:
            url: YouTube video URL
            max_comments: Maximum comments to retrieve
            sort: 'relevance' or 'time'

        Returns:
            CommentResult with comments and analytics
        """
        from .core.comments import CommentFilters, CommentOrder

        order = CommentOrder.RELEVANCE if sort == 'relevance' else CommentOrder.TIME
        filters = CommentFilters(order=order, max_results=max_comments)

        return self._toolkit.comments(url, filters=filters)

    def captions(self, url: str) -> Dict[str, Any]:
        """
        Get caption/subtitle analysis.

        Args:
            url: YouTube video URL

        Returns:
            CaptionResult with available tracks and analytics
        """
        return self._toolkit.captions(url)

    def sponsorblock(self, url: str) -> List[Dict[str, Any]]:
        """
        Get SponsorBlock segments for a video.

        Returns list of segments with:
        - category: 'sponsor', 'selfpromo', 'intro', 'outro', etc.
        - start_time, end_time, duration
        - description, votes

        Args:
            url: YouTube video URL

        Returns:
            List of segment dictionaries
        """
        return self._toolkit.get_sponsorblock_segments(url)

    def channel(self, channel: str) -> Dict[str, Any]:
        """
        Get channel analytics and information.

        Args:
            channel: Channel URL, handle (@name), or ID

        Returns:
            Dict with channel statistics, branding, topics, etc.
        """
        # Try YouTube API first for comprehensive info
        try:
            # Extract channel ID if needed
            if channel.startswith('@'):
                return self._toolkit.get_channel_info_full(handle=channel)
            elif channel.startswith('UC'):
                return self._toolkit.get_channel_info_full(channel_id=channel)
            else:
                return self._toolkit.get_channel_info(channel)
        except Exception:
            return self._toolkit.get_channel_info(channel)

    def filesize(self, url: str) -> Dict[str, Any]:
        """
        Get filesize preview for available streams without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Dict with filesize info for best audio/video streams
        """
        return self._toolkit.get_filesize_preview(url)


# =============================================================================
# STREAM API - Stream content (NEW in v1.0)
# =============================================================================

class LiveStreamSubAPI:
    """Sub-API for live stream operations."""

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit

    def status(self, url: str) -> Dict[str, Any]:
        """
        Get live stream status.

        Returns:
            Dict with is_live, was_live, live_status, release_timestamp
        """
        return self._toolkit.get_live_status(url)

    def is_live(self, url: str) -> bool:
        """
        Check if a video is currently live.

        Args:
            url: YouTube video URL

        Returns:
            True if currently live streaming
        """
        status = self.status(url)
        return status.get('is_live', False)

    def download(self, url: str, output_path: Optional[str] = None,
                 from_start: bool = False,
                 duration: Optional[int] = None) -> str:
        """
        Download a live stream.

        Args:
            url: YouTube live stream URL
            output_path: Output directory
            from_start: Download from beginning of stream
            duration: Max duration in seconds

        Returns:
            Path to downloaded file
        """
        return self._toolkit.download_live_stream(url, output_path, from_start, duration)


class StreamAPI:
    """
    STREAM API - Stream YouTube content to buffer.

    Usage:
        buffer = toolkit.stream(url)                    # Audio buffer (default)
        buffer = toolkit.stream.audio(url)              # Audio buffer
        buffer = toolkit.stream.video(url)              # Video buffer
        status = toolkit.stream.live.status(url)        # Live stream status
        is_live = toolkit.stream.live.is_live(url)      # Check if live
    """

    def __init__(self, toolkit: 'YouTubeToolkit'):
        self._toolkit = toolkit
        self.live = LiveStreamSubAPI(toolkit)

    def __call__(self, url: str, stream_type: str = 'audio',
                 quality: str = 'best') -> bytes:
        """
        Stream content to buffer.

        Args:
            url: YouTube video URL
            stream_type: 'audio' or 'video'
            quality: Stream quality

        Returns:
            Bytes containing the stream data
        """
        return self._toolkit.stream_to_buffer(url, stream_type, quality)

    def audio(self, url: str, quality: str = 'best') -> bytes:
        """
        Stream audio content to buffer.

        Args:
            url: YouTube video URL
            quality: Audio quality ('best', '128k', '192k', '256k')

        Returns:
            Bytes containing the audio data
        """
        return self._toolkit.stream_to_buffer(url, 'audio', quality)

    def video(self, url: str, quality: str = 'best') -> bytes:
        """
        Stream video content to buffer.

        Args:
            url: YouTube video URL
            quality: Video quality ('best', '1080p', '720p', '480p', '360p')

        Returns:
            Bytes containing the video data
        """
        return self._toolkit.stream_to_buffer(url, 'video', quality)

