"""
analyze.py — engagement / live / sponsorblock analysis service.

Holds the business logic for analysis-domain methods descended out of
YouTubeToolkit (api.py). api.py keeps one-line delegations to this service;
each method here is a verbatim move of the original body with self.* rewritten
to self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit.
"""

from typing import List, Dict, Any


class AnalyzeService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_sponsorblock_segments(self, url: str) -> List[Dict[str, Any]]:
        return self._toolkit.yt_dlp.get_sponsorblock_segments(url)

    def get_live_status(self, url: str) -> Dict[str, Any]:
        return self._toolkit.yt_dlp.get_live_status(url)

    def is_live(self, url: str) -> bool:
        status = self._toolkit.get_live_status(url)
        return status.get('is_live', False)

    def get_heatmap(self, url: str) -> List[Dict[str, Any]]:
        # Try yt-dlp first (more reliable for heatmap)
        try:
            result = self._toolkit.yt_dlp.get_heatmap(url)
            if result:
                return result
        except Exception:
            pass

        # Fallback to pytubefix
        try:
            return self._toolkit.pytubefix.get_replayed_heatmap(url)
        except Exception:
            return []

    def get_replayed_heatmap(self, url: str) -> List[Dict[str, Any]]:
        return self._toolkit.pytubefix.get_replayed_heatmap(url)
