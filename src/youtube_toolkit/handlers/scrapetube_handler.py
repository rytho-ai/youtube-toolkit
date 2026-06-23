"""ScrapeTube handler for YouTube Toolkit.

This handler implements channel scraping and search functionality
using the scrapetube package - a stable, lightweight library that can
retrieve ALL channel videos without pagination limits.

Key advantages:
- Get unlimited channel videos (no 500 video limit like API)
- No API quota usage
- Supports videos, shorts, and streams separately
- Generator-based for memory efficiency
- Proxy support for rate limiting avoidance
"""

from typing import Optional, Dict, Any, List, Generator


class ScrapeTubeHandler:
    """
    Handler for scrapetube package functionality.

    ScrapeTube is a stable scraper (471+ stars) that can retrieve
    ALL videos from a channel without pagination limits.

    Features:
    - get_channel_videos: Get all videos from a channel (unlimited!)
    - get_channel_shorts: Get all shorts from a channel
    - get_channel_streams: Get all streams from a channel
    - search: Search YouTube videos
    - get_playlist_videos: Get videos from a playlist
    - get_video: Get single video metadata

    Example:
        >>> handler = ScrapeTubeHandler()
        >>> videos = handler.get_channel_videos("@Fireship", limit=100)
        >>> for v in videos:
        ...     print(v['title'])
    """

    def __init__(self, sleep: float = 1.0, proxies: Optional[Dict[str, str]] = None):
        """
        Initialize the ScrapeTube handler.

        Args:
            sleep: Delay between requests in seconds (default: 1.0)
                   Higher values reduce rate limiting risk
            proxies: Optional proxy configuration dict
                     Example: {'http': 'http://proxy:8080', 'https': 'https://proxy:8080'}
        """
        self._scrapetube = None
        self._initialized = False
        self._available = False
        self.sleep = sleep
        self.proxies = proxies

    def _ensure_initialized(self):
        """Ensure scrapetube is available and initialized."""
        if not self._initialized:
            try:
                import scrapetube
                self._scrapetube = scrapetube
                self._available = True
                self._initialized = True
            except ImportError:
                self._available = False
                self._initialized = True

        if not self._available:
            raise ImportError(
                "scrapetube is not installed. Install with: "
                "pip install youtube-toolkit[scrapers] or pip install scrapetube"
            )

    @property
    def is_available(self) -> bool:
        """Check if scrapetube is installed and available."""
        try:
            self._ensure_initialized()
            return True
        except ImportError:
            return False

    # =========================================================================
    # Channel Methods
    # =========================================================================

    def get_channel_videos(self, channel: str,
                           limit: Optional[int] = None,
                           sort_by: str = 'newest') -> List[Dict[str, Any]]:
        """
        Get ALL videos from a YouTube channel (no pagination limit!).

        This is the primary advantage of scrapetube - it can retrieve
        ALL videos from a channel, unlike YouTube API which limits to 500.

        Args:
            channel: Channel identifier - can be:
                     - Channel ID: "UCsBjURrPoezykLs9EqgamOA"
                     - Handle: "@Fireship" or "Fireship"
                     - URL: "https://www.youtube.com/@Fireship"
            limit: Maximum videos to return (None = ALL videos)
            sort_by: Sort order - 'newest' (default), 'oldest', or 'popular'

        Returns:
            List of video dicts with: video_id, title, views, duration,
            published, thumbnail, channel

        Example:
            >>> # Get first 50 videos from Fireship
            >>> videos = handler.get_channel_videos("@Fireship", limit=50)
            >>>
            >>> # Get ALL videos (may take time for large channels)
            >>> all_videos = handler.get_channel_videos("@Fireship")
        """
        self._ensure_initialized()

        # Parse channel identifier
        channel_id, channel_url, username = self._parse_channel_identifier(channel)

        # Map sort_by to scrapetube format
        sort_map = {
            'newest': 'newest',
            'oldest': 'oldest',
            'popular': 'popular',
        }
        sort_value = sort_map.get(sort_by, 'newest')

        # Build kwargs for scrapetube
        kwargs = {
            'limit': limit,
            'sleep': self.sleep,
            'sort_by': sort_value,
            'content_type': 'videos',
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        # Call appropriate scrapetube function
        if channel_id:
            kwargs['channel_id'] = channel_id
        elif channel_url:
            kwargs['channel_url'] = channel_url
        elif username:
            kwargs['channel_username'] = username

        # Get generator and convert to list
        generator = self._scrapetube.get_channel(**kwargs)

        return [self._parse_video_result(raw) for raw in generator]

    def get_channel_shorts(self, channel: str,
                           limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all Shorts from a YouTube channel.

        Args:
            channel: Channel identifier (ID, handle, or URL)
            limit: Maximum shorts to return (None = all)

        Returns:
            List of shorts video dicts
        """
        self._ensure_initialized()

        channel_id, channel_url, username = self._parse_channel_identifier(channel)

        kwargs = {
            'limit': limit,
            'sleep': self.sleep,
            'content_type': 'shorts',
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        if channel_id:
            kwargs['channel_id'] = channel_id
        elif channel_url:
            kwargs['channel_url'] = channel_url
        elif username:
            kwargs['channel_username'] = username

        generator = self._scrapetube.get_channel(**kwargs)

        return [self._parse_video_result(raw) for raw in generator]

    def get_channel_streams(self, channel: str,
                            limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all streams (live/past broadcasts) from a YouTube channel.

        Args:
            channel: Channel identifier (ID, handle, or URL)
            limit: Maximum streams to return (None = all)

        Returns:
            List of stream video dicts
        """
        self._ensure_initialized()

        channel_id, channel_url, username = self._parse_channel_identifier(channel)

        kwargs = {
            'limit': limit,
            'sleep': self.sleep,
            'content_type': 'streams',
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        if channel_id:
            kwargs['channel_id'] = channel_id
        elif channel_url:
            kwargs['channel_url'] = channel_url
        elif username:
            kwargs['channel_username'] = username

        generator = self._scrapetube.get_channel(**kwargs)

        return [self._parse_video_result(raw) for raw in generator]

    def get_channel_videos_generator(self, channel: str,
                                     limit: Optional[int] = None,
                                     sort_by: str = 'newest',
                                     content_type: str = 'videos') -> Generator[Dict[str, Any], None, None]:
        """
        Get channel videos as a generator for memory efficiency.

        Use this for very large channels where loading all videos
        into memory at once would be problematic.

        Args:
            channel: Channel identifier (ID, handle, or URL)
            limit: Maximum videos to yield (None = all)
            sort_by: Sort order - 'newest', 'oldest', or 'popular'
            content_type: 'videos', 'shorts', or 'streams'

        Yields:
            Video dicts one at a time

        Example:
            >>> for video in handler.get_channel_videos_generator("@Fireship"):
            ...     print(video['title'])
            ...     # Process one video at a time
        """
        self._ensure_initialized()

        channel_id, channel_url, username = self._parse_channel_identifier(channel)

        kwargs = {
            'limit': limit,
            'sleep': self.sleep,
            'sort_by': sort_by if sort_by in ['newest', 'oldest', 'popular'] else 'newest',
            'content_type': content_type,
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        if channel_id:
            kwargs['channel_id'] = channel_id
        elif channel_url:
            kwargs['channel_url'] = channel_url
        elif username:
            kwargs['channel_username'] = username

        generator = self._scrapetube.get_channel(**kwargs)

        for raw in generator:
            yield self._parse_video_result(raw)

    # =========================================================================
    # Search Methods
    # =========================================================================

    def search(self, query: str,
               limit: int = 20,
               sort_by: str = 'relevance',
               results_type: str = 'video') -> List[Dict[str, Any]]:
        """
        Search YouTube videos without API quota.

        Args:
            query: Search query string
            limit: Maximum results to return (default: 20)
            sort_by: Sort order - 'relevance' (default), 'upload_date',
                     'view_count', 'rating'
            results_type: Type of results - 'video' (default), 'channel', 'playlist'

        Returns:
            List of search result dicts

        Example:
            >>> results = handler.search("python tutorial", limit=10)
            >>> results = handler.search("music", sort_by='view_count')
        """
        self._ensure_initialized()

        kwargs = {
            'query': query,
            'limit': limit,
            'sleep': self.sleep,
            'sort_by': sort_by,
            'results_type': results_type,
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        generator = self._scrapetube.get_search(**kwargs)

        return [self._parse_video_result(raw) for raw in generator]

    # =========================================================================
    # Playlist Methods
    # =========================================================================

    def get_playlist_videos(self, playlist_id: str,
                            limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get videos from a YouTube playlist.

        Args:
            playlist_id: YouTube playlist ID (e.g., "PLxxxxxxx") or full URL
            limit: Maximum videos to return (None = all)

        Returns:
            List of video dicts
        """
        self._ensure_initialized()

        # Extract playlist ID from URL if needed
        if 'youtube.com' in playlist_id or 'youtu.be' in playlist_id:
            import re
            match = re.search(r'list=([a-zA-Z0-9_-]+)', playlist_id)
            if match:
                playlist_id = match.group(1)

        kwargs = {
            'playlist_id': playlist_id,
            'limit': limit,
            'sleep': self.sleep,
        }
        if self.proxies:
            kwargs['proxies'] = self.proxies

        generator = self._scrapetube.get_playlist(**kwargs)

        return [self._parse_video_result(raw) for raw in generator]

    # =========================================================================
    # Single Video Methods
    # =========================================================================

    def get_video(self, video_id: str) -> Dict[str, Any]:
        """
        Get metadata for a single video.

        Args:
            video_id: YouTube video ID or full URL

        Returns:
            Video metadata dict
        """
        self._ensure_initialized()

        # Extract video ID from URL if needed
        if 'youtube.com' in video_id or 'youtu.be' in video_id:
            import re
            # Handle various URL formats
            patterns = [
                r'v=([a-zA-Z0-9_-]{11})',
                r'youtu\.be/([a-zA-Z0-9_-]{11})',
                r'embed/([a-zA-Z0-9_-]{11})',
            ]
            for pattern in patterns:
                match = re.search(pattern, video_id)
                if match:
                    video_id = match.group(1)
                    break

        raw = self._scrapetube.get_video(video_id)

        return self._parse_video_result(raw) if raw else {}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_channel_identifier(self, channel: str) -> tuple:
        """
        Parse channel identifier into (channel_id, channel_url, username).

        Returns tuple where only one value is set based on input type.
        """
        import re

        channel = channel.strip()

        # Full URL
        if 'youtube.com' in channel:
            # Extract handle from URL: youtube.com/@handle
            handle_match = re.search(r'youtube\.com/@([a-zA-Z0-9_-]+)', channel)
            if handle_match:
                return (None, channel, None)

            # Extract channel ID from URL: youtube.com/channel/UC...
            id_match = re.search(r'youtube\.com/channel/([a-zA-Z0-9_-]+)', channel)
            if id_match:
                return (id_match.group(1), None, None)

            # Custom URL: youtube.com/c/name
            custom_match = re.search(r'youtube\.com/c/([a-zA-Z0-9_-]+)', channel)
            if custom_match:
                return (None, channel, None)

            # Fallback: use as URL
            return (None, channel, None)

        # Handle format: @username
        if channel.startswith('@'):
            return (None, f"https://www.youtube.com/{channel}", None)

        # Channel ID format: starts with UC and is 24 chars
        if channel.startswith('UC') and len(channel) == 24:
            return (channel, None, None)

        # Assume it's a username
        return (None, None, channel)

    def _parse_video_result(self, raw: dict) -> Dict[str, Any]:
        """
        Parse raw YouTube JSON response to clean format.

        ScrapeTube returns raw YouTube innertube API responses which have
        nested structures. This method extracts the relevant fields.
        """
        if not raw:
            return {}

        # Extract video ID
        video_id = raw.get('videoId', '')

        # Extract title - can be in different places
        title = ''
        if 'title' in raw:
            title_obj = raw['title']
            if isinstance(title_obj, dict):
                runs = title_obj.get('runs', [])
                if runs:
                    title = runs[0].get('text', '')
                else:
                    title = title_obj.get('simpleText', '')
            else:
                title = str(title_obj)

        # Extract channel/author
        channel = ''
        channel_id = ''
        if 'ownerText' in raw:
            runs = raw['ownerText'].get('runs', [])
            if runs:
                channel = runs[0].get('text', '')
                nav = runs[0].get('navigationEndpoint', {})
                channel_id = nav.get('browseEndpoint', {}).get('browseId', '')
        elif 'longBylineText' in raw:
            runs = raw['longBylineText'].get('runs', [])
            if runs:
                channel = runs[0].get('text', '')
        elif 'shortBylineText' in raw:
            runs = raw['shortBylineText'].get('runs', [])
            if runs:
                channel = runs[0].get('text', '')

        # Extract view count
        views = 0
        views_text = ''
        if 'viewCountText' in raw:
            vct = raw['viewCountText']
            if isinstance(vct, dict):
                views_text = vct.get('simpleText', '') or ''
                # Also check for 'runs' format
                if not views_text and 'runs' in vct:
                    views_text = ''.join(r.get('text', '') for r in vct['runs'])
            else:
                views_text = str(vct)

            # Parse view count to int
            views = self._parse_view_count(views_text)

        # Extract duration
        duration = 0
        duration_text = ''
        if 'lengthText' in raw:
            lt = raw['lengthText']
            if isinstance(lt, dict):
                duration_text = lt.get('simpleText', '') or lt.get('accessibility', {}).get('accessibilityData', {}).get('label', '')
            else:
                duration_text = str(lt)
            duration = self._parse_duration(duration_text)

        # Extract published time
        published = ''
        if 'publishedTimeText' in raw:
            ptt = raw['publishedTimeText']
            if isinstance(ptt, dict):
                published = ptt.get('simpleText', '')
            else:
                published = str(ptt)

        # Extract thumbnail
        thumbnail = ''
        if 'thumbnail' in raw:
            thumbs = raw['thumbnail'].get('thumbnails', [])
            if thumbs:
                # Get highest resolution thumbnail
                thumbnail = thumbs[-1].get('url', '')

        # Extract description snippet if available
        description = ''
        if 'descriptionSnippet' in raw:
            runs = raw['descriptionSnippet'].get('runs', [])
            description = ''.join(r.get('text', '') for r in runs)

        return {
            'video_id': video_id,
            'title': title,
            'channel': channel,
            'channel_id': channel_id,
            'views': views,
            'views_text': views_text,
            'duration': duration,
            'duration_text': duration_text,
            'published': published,
            'thumbnail': thumbnail,
            'description': description[:200] if description else '',
            'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else '',
        }

    def _parse_view_count(self, text: str) -> int:
        """Parse view count text to integer."""
        import re

        if not text:
            return 0

        # Remove non-numeric characters except K, M, B
        text = text.upper().replace(',', '').replace(' ', '')

        # Handle "1.2M views" format
        multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}

        for suffix, mult in multipliers.items():
            if suffix in text:
                try:
                    num = float(re.search(r'[\d.]+', text).group())
                    return int(num * mult)
                except:
                    pass

        # Try to extract plain number
        try:
            return int(re.sub(r'[^\d]', '', text))
        except:
            return 0

    def _parse_duration(self, text: str) -> int:
        """Parse duration text to seconds."""
        import re

        if not text:
            return 0

        # Handle "HH:MM:SS" or "MM:SS" format
        parts = text.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                return int(parts[0])
        except:
            pass

        # Handle "X hours Y minutes Z seconds" format
        total = 0
        hours = re.search(r'(\d+)\s*hour', text, re.IGNORECASE)
        minutes = re.search(r'(\d+)\s*minute', text, re.IGNORECASE)
        seconds = re.search(r'(\d+)\s*second', text, re.IGNORECASE)

        if hours:
            total += int(hours.group(1)) * 3600
        if minutes:
            total += int(minutes.group(1)) * 60
        if seconds:
            total += int(seconds.group(1))

        return total
