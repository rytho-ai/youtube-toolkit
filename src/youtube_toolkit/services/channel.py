"""
channel.py — channel-domain service.

Holds channel listing/metadata/subscription/activity logic descended out of
YouTubeToolkit (api.py). api.py keeps one-line delegations; bodies here are
verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.handlers.scrapetube_handler (lazy import).
"""

from typing import Optional, List, Dict, Any


class ChannelService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_channel_videos(self, channel: str,
                           content_type: str = 'videos',
                           limit: Optional[int] = None,
                           sort_by: str = 'newest',
                           use_scrapetube: bool = False) -> List[Dict[str, Any]]:
        if use_scrapetube:
            # Try scrapetube for unlimited results
            try:
                from ..handlers.scrapetube_handler import ScrapeTubeHandler
                scrapetube = ScrapeTubeHandler()

                if content_type == 'videos':
                    return scrapetube.get_channel_videos(channel, limit=limit, sort_by=sort_by)
                elif content_type == 'shorts':
                    return scrapetube.get_channel_shorts(channel, limit=limit)
                elif content_type == 'live':
                    return scrapetube.get_channel_streams(channel, limit=limit)
                else:
                    # Fallback to pytubefix for playlists
                    return self._toolkit.pytubefix.get_channel_videos(channel, content_type, limit, sort_by)

            except ImportError:
                if self._toolkit.verbose:
                    print("⚠️ scrapetube not installed. Falling back to pytubefix.")
                    print("   Install with: pip install youtube-toolkit[scrapers]")

        # Use pytubefix (default)
        return self._toolkit.pytubefix.get_channel_videos(channel, content_type, limit, sort_by)

    def get_channel_info(self, channel_url: str) -> Dict[str, Any]:
        return self._toolkit.pytubefix.get_channel_info(channel_url)

    def get_all_channel_videos(self, channel: str,
                               content_type: str = 'videos') -> List[Dict[str, Any]]:
        try:
            from ..handlers.scrapetube_handler import ScrapeTubeHandler
            scrapetube = ScrapeTubeHandler()

            if content_type == 'videos':
                return scrapetube.get_channel_videos(channel, limit=None)
            elif content_type == 'shorts':
                return scrapetube.get_channel_shorts(channel, limit=None)
            elif content_type == 'streams':
                return scrapetube.get_channel_streams(channel, limit=None)
            else:
                raise ValueError(f"Invalid content_type: {content_type}")

        except ImportError:
            raise ImportError(
                "scrapetube is required for unlimited channel videos. "
                "Install with: pip install youtube-toolkit[scrapers]"
            )

    def get_channel_shorts(self, channel_url: str, max_results: int = 50) -> List[Dict[str, Any]]:
        return self._toolkit.yt_dlp.get_channel_shorts(channel_url, max_results)

    def get_channel_subscriptions(self, channel_id: str, max_results: int = 50,
                                  order: str = 'relevance',
                                  page_token: str = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_channel_subscriptions(channel_id, max_results, order, page_token)

    def check_subscription(self, channel_id: str, target_channel_id: str) -> Dict[str, Any]:
        return self._toolkit.youtube_api.check_subscription(channel_id, target_channel_id)

    def get_channel_activities(self, channel_id: str, max_results: int = 25,
                              published_after: str = None,
                              published_before: str = None,
                              region_code: str = None,
                              page_token: str = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_channel_activities(
            channel_id, max_results, published_after, published_before, region_code, page_token
        )

    def get_recent_uploads(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_recent_uploads(channel_id, max_results)

    def get_channel_sections(self, channel_id: str,
                            language: str = None) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_channel_sections(channel_id, language)

    def get_channel_featured_channels(self, channel_id: str) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_channel_featured_channels(channel_id)

    def get_channel_info_full(self, channel_id: str = None,
                              username: str = None,
                              handle: str = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.get_channel_info(channel_id, username, handle)

    def get_multiple_channels(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_multiple_channels(channel_ids)
