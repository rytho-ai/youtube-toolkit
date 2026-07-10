"""Follow-up fixes: channel shorts/streams sort_by exposure + sorting, and
playlist.videos returning a consistent list-of-dicts (not bare URL strings).
Mock at the service/handler boundary per the project's testing convention.
"""

from unittest.mock import MagicMock, patch

from youtube_toolkit.services.channel import _sort_channel_items


class TestSortChannelItems:
    def _items(self):
        return [{"title": "a", "views": 5}, {"title": "b", "views": 50}, {"title": "c", "views": 10}]

    def test_popular_sorts_by_views_desc(self):
        assert [x["title"] for x in _sort_channel_items(self._items(), "popular")] == ["b", "c", "a"]

    def test_oldest_reverses(self):
        assert [x["title"] for x in _sort_channel_items(self._items(), "oldest")] == ["c", "b", "a"]

    def test_newest_unchanged(self):
        assert [x["title"] for x in _sort_channel_items(self._items(), "newest")] == ["a", "b", "c"]

    def test_empty_and_missing_views_safe(self):
        assert _sort_channel_items([], "popular") == []
        # a missing/None 'views' must not crash the popular sort
        _sort_channel_items([{"title": "x"}, {"title": "y", "views": None}], "popular")


class TestChannelFacadeSortByPassthrough:
    """The .shorts/.streams facades now expose sort_by and forward it to the
    service with the right content_type (was: sort_by unreachable for these)."""

    def _toolkit(self):
        from youtube_toolkit.sub_apis import ChannelGetAPI

        tk = MagicMock()
        tk._channel.get_channel_videos.return_value = []
        parent = MagicMock()
        parent._toolkit = tk
        return ChannelGetAPI(parent), tk

    def test_shorts_forwards_sort_by(self):
        api, tk = self._toolkit()
        api.shorts("@chan", limit=5, sort_by="popular")
        _, kwargs = tk._channel.get_channel_videos.call_args
        assert kwargs["content_type"] == "shorts"
        assert kwargs["sort_by"] == "popular"

    def test_streams_forwards_sort_by(self):
        api, tk = self._toolkit()
        api.streams("@chan", sort_by="oldest")
        _, kwargs = tk._channel.get_channel_videos.call_args
        assert kwargs["content_type"] == "live"
        assert kwargs["sort_by"] == "oldest"


class TestPlaylistVideosAlwaysDicts:
    def test_url_path_returns_dicts_not_strings(self):
        from youtube_toolkit.services.playlist import PlaylistService

        tk = MagicMock()
        tk.extract_video_id.side_effect = lambda u: u.rsplit("=", 1)[-1].rsplit("/", 1)[-1]
        svc = PlaylistService(tk)
        with patch.object(
            svc, "get_playlist_urls",
            return_value=["https://www.youtube.com/watch?v=AAA", "https://youtu.be/BBB"],
        ):
            out = svc.get_playlist_videos("x")
        assert all(isinstance(d, dict) for d in out)
        assert out[0] == {"url": "https://www.youtube.com/watch?v=AAA", "video_id": "AAA"}
        assert out[1]["video_id"] == "BBB"

    def test_limit_is_applied(self):
        from youtube_toolkit.services.playlist import PlaylistService

        tk = MagicMock()
        tk.extract_video_id.side_effect = lambda u: u[-1]
        svc = PlaylistService(tk)
        with patch.object(svc, "get_playlist_urls", return_value=["a", "b", "c", "d"]):
            out = svc.get_playlist_videos("x", limit=2)
        assert len(out) == 2
