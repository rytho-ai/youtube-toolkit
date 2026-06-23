"""
Tests for channel-related features (v0.3+).

Tests cover:
- PyTubeFixHandler: get_channel_videos, get_channel_info, get_video_chapters,
  get_key_moments, get_replayed_heatmap, advanced_search, get_playlist_info
- ScrapeTubeHandler: channel videos, shorts, streams, search, playlist
- YouTubeToolkit: integration of channel features
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List, Dict, Any


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_channel_url():
    """Sample channel URL for testing."""
    return "https://www.youtube.com/@Fireship"


@pytest.fixture
def sample_channel_id():
    """Sample channel ID for testing."""
    return "UCsBjURrPoezykLs9EqgamOA"


@pytest.fixture
def sample_channel_info():
    """Sample channel info response."""
    return {
        'channel_name': 'Fireship',
        'channel_id': 'UCsBjURrPoezykLs9EqgamOA',
        'channel_url': 'https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA',
        'vanity_url': 'https://www.youtube.com/@Fireship',
        'description': 'High-intensity code tutorials',
        'thumbnail_url': 'https://yt3.ggpht.com/...',
        'total_views': 100000000,
        'video_count': 500,
        'last_updated': None,
    }


@pytest.fixture
def sample_channel_videos():
    """Sample channel videos response."""
    return [
        {
            'video_id': 'abc123',
            'title': 'Video 1',
            'url': 'https://www.youtube.com/watch?v=abc123',
            'author': 'Fireship',
            'length': 300,
            'views': 100000,
            'publish_date': '2024-01-15',
            'thumbnail_url': 'https://i.ytimg.com/vi/abc123/maxresdefault.jpg',
        },
        {
            'video_id': 'def456',
            'title': 'Video 2',
            'url': 'https://www.youtube.com/watch?v=def456',
            'author': 'Fireship',
            'length': 600,
            'views': 200000,
            'publish_date': '2024-01-10',
            'thumbnail_url': 'https://i.ytimg.com/vi/def456/maxresdefault.jpg',
        },
    ]


@pytest.fixture
def sample_chapters():
    """Sample video chapters response."""
    return [
        {
            'title': 'Introduction',
            'start_seconds': 0,
            'duration': 60,
            'end_seconds': 60,
            'formatted_start': '0:00',
        },
        {
            'title': 'Main Content',
            'start_seconds': 60,
            'duration': 180,
            'end_seconds': 240,
            'formatted_start': '1:00',
        },
        {
            'title': 'Conclusion',
            'start_seconds': 240,
            'duration': 60,
            'end_seconds': 300,
            'formatted_start': '4:00',
        },
    ]


@pytest.fixture
def sample_playlist_info():
    """Sample playlist info response."""
    return {
        'playlist_id': 'PLxxxxxxx',
        'title': 'Python Tutorials',
        'description': 'Learn Python programming',
        'owner': 'Fireship',
        'owner_id': 'UCsBjURrPoezykLs9EqgamOA',
        'owner_url': 'https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA',
        'video_count': 50,
        'views': 1000000,
        'last_updated': '2024-01-20',
        'thumbnail_url': 'https://i.ytimg.com/vi/.../maxresdefault.jpg',
    }


@pytest.fixture
def sample_scrapetube_raw_video():
    """Sample raw scrapetube video response."""
    return {
        'videoId': 'abc123',
        'title': {'runs': [{'text': 'Test Video Title'}]},
        'ownerText': {'runs': [{'text': 'Test Channel'}]},
        'viewCountText': {'simpleText': '1.5M views'},
        'lengthText': {'simpleText': '10:30'},
        'publishedTimeText': {'simpleText': '2 weeks ago'},
        'thumbnail': {'thumbnails': [{'url': 'https://i.ytimg.com/vi/abc123/default.jpg'}]},
    }


# =============================================================================
# PyTubeFixHandler Tests
# =============================================================================

class TestPyTubeFixHandlerChannel:
    """Tests for PyTubeFixHandler channel methods."""

    def test_get_channel_videos_returns_list(self, sample_channel_url, sample_channel_videos):
        """Test get_channel_videos returns a list of video dicts."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.Channel') as mock_channel:
                # Setup mock
                mock_channel_instance = MagicMock()
                mock_video1 = MagicMock()
                mock_video1.video_id = 'abc123'
                mock_video1.title = 'Video 1'
                mock_video1.watch_url = 'https://www.youtube.com/watch?v=abc123'
                mock_video1.author = 'Fireship'
                mock_video1.length = 300
                mock_video1.views = 100000
                mock_video1.publish_date = '2024-01-15'
                mock_video1.thumbnail_url = 'https://i.ytimg.com/vi/abc123/maxresdefault.jpg'

                mock_channel_instance.videos = [mock_video1]
                mock_channel.return_value = mock_channel_instance

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_channel_videos(sample_channel_url, limit=10)

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]['video_id'] == 'abc123'
                assert result[0]['title'] == 'Video 1'

    def test_get_channel_videos_with_content_type_shorts(self, sample_channel_url):
        """Test get_channel_videos with content_type='shorts'."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.Channel') as mock_channel:
                mock_channel_instance = MagicMock()
                mock_short = MagicMock()
                mock_short.video_id = 'short123'
                mock_short.title = 'Short Video'
                mock_short.watch_url = 'https://www.youtube.com/shorts/short123'
                mock_short.author = 'Fireship'
                mock_short.length = 30
                mock_short.views = 50000
                mock_short.publish_date = None
                mock_short.thumbnail_url = None

                mock_channel_instance.shorts = [mock_short]
                mock_channel.return_value = mock_channel_instance

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_channel_videos(sample_channel_url, content_type='shorts')

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]['video_id'] == 'short123'

    def test_get_channel_videos_invalid_content_type(self, sample_channel_url):
        """Test get_channel_videos raises error for invalid content_type."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.Channel') as mock_channel:
                mock_channel.return_value = MagicMock()

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                # The error is wrapped in RuntimeError by the exception handler
                with pytest.raises(RuntimeError, match="Invalid content_type"):
                    handler.get_channel_videos(sample_channel_url, content_type='invalid')

    def test_get_channel_info_returns_dict(self, sample_channel_url, sample_channel_info):
        """Test get_channel_info returns channel metadata dict."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.Channel') as mock_channel:
                mock_channel_instance = MagicMock()
                mock_channel_instance.channel_name = 'Fireship'
                mock_channel_instance.channel_id = 'UCsBjURrPoezykLs9EqgamOA'
                mock_channel_instance.channel_url = 'https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA'
                mock_channel_instance.vanity_url = 'https://www.youtube.com/@Fireship'
                mock_channel_instance.description = 'High-intensity code tutorials'
                mock_channel_instance.thumbnail_url = 'https://yt3.ggpht.com/...'
                mock_channel_instance.views = 100000000
                mock_channel_instance.length = 500
                mock_channel_instance.last_updated = None
                mock_channel.return_value = mock_channel_instance

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_channel_info(sample_channel_url)

                assert isinstance(result, dict)
                assert result['channel_name'] == 'Fireship'
                assert result['channel_id'] == 'UCsBjURrPoezykLs9EqgamOA'
                assert result['video_count'] == 500


class TestPyTubeFixHandlerChapters:
    """Tests for PyTubeFixHandler chapter methods."""

    def test_get_video_chapters_returns_list(self, sample_chapters):
        """Test get_video_chapters returns list of chapter dicts."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._create_yt') as mock_create:
                mock_yt = MagicMock()

                # Create mock chapters
                mock_chapter1 = MagicMock()
                mock_chapter1.title = 'Introduction'
                mock_chapter1.start_seconds = 0
                mock_chapter1.duration = 60

                mock_chapter2 = MagicMock()
                mock_chapter2.title = 'Main Content'
                mock_chapter2.start_seconds = 60
                mock_chapter2.duration = 180

                mock_yt.chapters = [mock_chapter1, mock_chapter2]
                mock_create.return_value = mock_yt

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_video_chapters("https://youtube.com/watch?v=test")

                assert isinstance(result, list)
                assert len(result) == 2
                assert result[0]['title'] == 'Introduction'
                assert result[0]['start_seconds'] == 0
                assert result[0]['formatted_start'] == '0:00'
                assert result[1]['title'] == 'Main Content'
                assert result[1]['formatted_start'] == '1:00'

    def test_get_video_chapters_empty_when_no_chapters(self):
        """Test get_video_chapters returns empty list when video has no chapters."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._create_yt') as mock_create:
                mock_yt = MagicMock()
                mock_yt.chapters = None
                mock_create.return_value = mock_yt

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_video_chapters("https://youtube.com/watch?v=test")

                assert result == []

    def test_get_video_chapters_formats_hours(self):
        """Test chapter formatting includes hours for long videos."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._create_yt') as mock_create:
                mock_yt = MagicMock()

                mock_chapter = MagicMock()
                mock_chapter.title = 'Late Chapter'
                mock_chapter.start_seconds = 3665  # 1:01:05
                mock_chapter.duration = 60

                mock_yt.chapters = [mock_chapter]
                mock_create.return_value = mock_yt

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_video_chapters("https://youtube.com/watch?v=test")

                assert result[0]['formatted_start'] == '1:01:05'

    def test_get_key_moments_returns_list(self):
        """Test get_key_moments returns list of key moment dicts."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._create_yt') as mock_create:
                mock_yt = MagicMock()

                mock_km = MagicMock()
                mock_km.title = 'Key Moment 1'
                mock_km.start_seconds = 120
                mock_km.duration = 30

                mock_yt.key_moments = [mock_km]
                mock_create.return_value = mock_yt

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_key_moments("https://youtube.com/watch?v=test")

                assert isinstance(result, list)
                assert len(result) == 1
                assert result[0]['title'] == 'Key Moment 1'

    def test_get_replayed_heatmap_returns_list(self):
        """Test get_replayed_heatmap returns heatmap data."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._create_yt') as mock_create:
                mock_yt = MagicMock()
                mock_yt.replayed_heatmap = [
                    {'start_seconds': 0, 'duration': 10, 'intensity': 0.5},
                    {'start_seconds': 10, 'duration': 10, 'intensity': 0.8},
                ]
                mock_create.return_value = mock_yt

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_replayed_heatmap("https://youtube.com/watch?v=test")

                assert isinstance(result, list)
                assert len(result) == 2


class TestPyTubeFixHandlerAdvancedSearch:
    """Tests for PyTubeFixHandler advanced_search method."""

    def test_advanced_search_basic(self):
        """Test advanced_search with basic query."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.contrib.search.Search') as mock_search_cls:
                with patch('pytubefix.contrib.search.Filter') as mock_filter:
                    # Setup filter mock
                    mock_filter_instance = MagicMock()
                    mock_filter.create.return_value = mock_filter_instance
                    mock_filter_instance.type.return_value = mock_filter_instance

                    # Setup search mock
                    mock_search = MagicMock()
                    mock_video = MagicMock()
                    mock_video.video_id = 'test123'
                    mock_video.title = 'Test Video'
                    mock_video.watch_url = 'https://youtube.com/watch?v=test123'
                    mock_video.author = 'Test Channel'
                    mock_video.length = 600
                    mock_video.views = 10000
                    mock_video.publish_date = None
                    mock_video.thumbnail_url = None
                    mock_video.description = 'Test description'

                    mock_search.videos = [mock_video]
                    mock_search.shorts = []
                    mock_search.channel = []
                    mock_search.playlist = []
                    mock_search.completion_suggestions = ['test suggestion']
                    mock_search_cls.return_value = mock_search

                    from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                    handler = PyTubeFixHandler()
                    handler._initialized = True

                    result = handler.advanced_search("python tutorial", max_results=10)

                    assert isinstance(result, dict)
                    assert 'videos' in result
                    assert 'query' in result
                    assert result['query'] == 'python tutorial'
                    assert len(result['videos']) == 1

    def test_advanced_search_with_filters(self):
        """Test advanced_search with duration and date filters."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.contrib.search.Search') as mock_search_cls:
                with patch('pytubefix.contrib.search.Filter') as mock_filter:
                    mock_filter_instance = MagicMock()
                    mock_filter.create.return_value = mock_filter_instance
                    mock_filter_instance.duration.return_value = mock_filter_instance
                    mock_filter_instance.upload_date.return_value = mock_filter_instance
                    mock_filter_instance.sort_by.return_value = mock_filter_instance
                    mock_filter_instance.type.return_value = mock_filter_instance

                    mock_filter.Duration.BETWEEN_4_20_MINUTES = 'medium'
                    mock_filter.UploadDate.THIS_MONTH = 'month'
                    mock_filter.SortBy.VIEW_COUNT = 'views'
                    mock_filter.Type.VIDEO = 'video'

                    mock_search = MagicMock()
                    mock_search.videos = []
                    mock_search.shorts = []
                    mock_search.channel = []
                    mock_search.playlist = []
                    mock_search.completion_suggestions = []
                    mock_search_cls.return_value = mock_search

                    from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                    handler = PyTubeFixHandler()
                    handler._initialized = True

                    result = handler.advanced_search(
                        "python",
                        duration='medium',
                        upload_date='month',
                        sort_by='views'
                    )

                    assert result['filters_applied']['duration'] == 'medium'
                    assert result['filters_applied']['upload_date'] == 'month'
                    assert result['filters_applied']['sort_by'] == 'views'


class TestPyTubeFixHandlerPlaylist:
    """Tests for PyTubeFixHandler playlist methods."""

    def test_get_playlist_info_returns_dict(self, sample_playlist_info):
        """Test get_playlist_info returns playlist metadata."""
        with patch('youtube_toolkit.handlers.pytubefix_handler.PyTubeFixHandler._ensure_initialized'):
            with patch('pytubefix.Playlist') as mock_playlist:
                mock_playlist_instance = MagicMock()
                mock_playlist_instance.playlist_id = 'PLxxxxxxx'
                mock_playlist_instance.title = 'Python Tutorials'
                mock_playlist_instance.description = 'Learn Python programming'
                mock_playlist_instance.owner = 'Fireship'
                mock_playlist_instance.owner_id = 'UCsBjURrPoezykLs9EqgamOA'
                mock_playlist_instance.owner_url = 'https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA'
                mock_playlist_instance.length = 50
                mock_playlist_instance.views = 1000000
                mock_playlist_instance.last_updated = '2024-01-20'
                mock_playlist_instance.thumbnail_url = 'https://i.ytimg.com/...'
                mock_playlist.return_value = mock_playlist_instance

                from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
                handler = PyTubeFixHandler()
                handler._initialized = True

                result = handler.get_playlist_info("https://youtube.com/playlist?list=PLxxxxxxx")

                assert isinstance(result, dict)
                assert result['playlist_id'] == 'PLxxxxxxx'
                assert result['title'] == 'Python Tutorials'
                assert result['video_count'] == 50


# =============================================================================
# ScrapeTubeHandler Tests
# =============================================================================

class TestScrapeTubeHandler:
    """Tests for ScrapeTubeHandler."""

    def test_is_available_when_installed(self):
        """Test is_available returns True when scrapetube is installed."""
        with patch.dict('sys.modules', {'scrapetube': MagicMock()}):
            from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
            handler = ScrapeTubeHandler()

            # Force re-initialization
            handler._initialized = False
            handler._available = False

            assert handler.is_available is True

    def test_is_available_when_not_installed(self):
        """Test is_available returns False when scrapetube is not installed."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()
        handler._initialized = True
        handler._available = False

        assert handler.is_available is False

    def test_parse_channel_identifier_url(self):
        """Test _parse_channel_identifier with full URL."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        channel_id, channel_url, username = handler._parse_channel_identifier(
            "https://www.youtube.com/@Fireship"
        )

        assert channel_url == "https://www.youtube.com/@Fireship"
        assert channel_id is None

    def test_parse_channel_identifier_handle(self):
        """Test _parse_channel_identifier with @handle."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        channel_id, channel_url, username = handler._parse_channel_identifier("@Fireship")

        assert channel_url == "https://www.youtube.com/@Fireship"
        assert channel_id is None

    def test_parse_channel_identifier_channel_id(self):
        """Test _parse_channel_identifier with channel ID."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        channel_id, channel_url, username = handler._parse_channel_identifier(
            "UCsBjURrPoezykLs9EqgamOA"
        )

        assert channel_id == "UCsBjURrPoezykLs9EqgamOA"
        assert channel_url is None

    def test_parse_video_result(self, sample_scrapetube_raw_video):
        """Test _parse_video_result parses raw YouTube JSON correctly."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        result = handler._parse_video_result(sample_scrapetube_raw_video)

        assert result['video_id'] == 'abc123'
        assert result['title'] == 'Test Video Title'
        assert result['channel'] == 'Test Channel'
        assert result['views'] == 1500000  # 1.5M
        assert result['duration'] == 630  # 10:30 = 10*60 + 30

    def test_parse_view_count_millions(self):
        """Test _parse_view_count handles M suffix."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        assert handler._parse_view_count("1.5M views") == 1500000
        assert handler._parse_view_count("2M views") == 2000000

    def test_parse_view_count_thousands(self):
        """Test _parse_view_count handles K suffix."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        assert handler._parse_view_count("500K views") == 500000
        assert handler._parse_view_count("1.2K views") == 1200

    def test_parse_view_count_plain_number(self):
        """Test _parse_view_count handles plain numbers."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        assert handler._parse_view_count("1,234,567 views") == 1234567
        assert handler._parse_view_count("12345") == 12345

    def test_parse_duration_mm_ss(self):
        """Test _parse_duration handles MM:SS format."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        assert handler._parse_duration("10:30") == 630
        assert handler._parse_duration("5:00") == 300

    def test_parse_duration_hh_mm_ss(self):
        """Test _parse_duration handles HH:MM:SS format."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        assert handler._parse_duration("1:30:00") == 5400
        assert handler._parse_duration("2:15:30") == 8130

    def test_get_channel_videos_with_mock(self, sample_scrapetube_raw_video):
        """Test get_channel_videos with mocked scrapetube."""
        with patch('youtube_toolkit.handlers.scrapetube_handler.ScrapeTubeHandler._ensure_initialized'):
            from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
            handler = ScrapeTubeHandler()
            handler._available = True
            handler._initialized = True

            mock_scrapetube = MagicMock()
            mock_scrapetube.get_channel.return_value = iter([sample_scrapetube_raw_video])
            handler._scrapetube = mock_scrapetube

            result = handler.get_channel_videos("@Fireship", limit=10)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]['video_id'] == 'abc123'

    def test_search_with_mock(self, sample_scrapetube_raw_video):
        """Test search with mocked scrapetube."""
        with patch('youtube_toolkit.handlers.scrapetube_handler.ScrapeTubeHandler._ensure_initialized'):
            from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
            handler = ScrapeTubeHandler()
            handler._available = True
            handler._initialized = True

            mock_scrapetube = MagicMock()
            mock_scrapetube.get_search.return_value = iter([sample_scrapetube_raw_video])
            handler._scrapetube = mock_scrapetube

            result = handler.search("python tutorial", limit=10)

            assert isinstance(result, list)
            assert len(result) == 1


# =============================================================================
# YouTubeToolkit Integration Tests
# =============================================================================

class TestYouTubeToolkitChannelFeatures:
    """Integration tests for YouTubeToolkit channel features."""

    def test_get_channel_videos_uses_pytubefix_by_default(self, sample_channel_videos):
        """Test get_channel_videos uses pytubefix by default."""
        with patch('youtube_toolkit.api.PyTubeFixHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.get_channel_videos.return_value = sample_channel_videos
            mock_handler_cls.return_value = mock_handler

            with patch('youtube_toolkit.api.YTDLPHandler'):
                with patch('youtube_toolkit.api.YouTubeAPIHandler'):
                    from youtube_toolkit import YouTubeToolkit
                    toolkit = YouTubeToolkit()
                    toolkit.pytubefix = mock_handler

                    result = toolkit.get.channel.videos("@Fireship", limit=50)

                    mock_handler.get_channel_videos.assert_called_once()
                    assert result == sample_channel_videos

    def test_get_channel_info(self, sample_channel_info):
        """Test get_channel_info delegates to pytubefix."""
        with patch('youtube_toolkit.api.PyTubeFixHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.get_channel_info.return_value = sample_channel_info
            mock_handler_cls.return_value = mock_handler

            with patch('youtube_toolkit.api.YTDLPHandler'):
                with patch('youtube_toolkit.api.YouTubeAPIHandler'):
                    from youtube_toolkit import YouTubeToolkit
                    toolkit = YouTubeToolkit()
                    toolkit.pytubefix = mock_handler

                    result = toolkit.get.channel("@Fireship")

                    assert result['channel_name'] == 'Fireship'

    def test_get_video_chapters(self, sample_chapters):
        """Test get_video_chapters delegates to pytubefix."""
        with patch('youtube_toolkit.api.PyTubeFixHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.get_video_chapters.return_value = sample_chapters
            mock_handler_cls.return_value = mock_handler

            with patch('youtube_toolkit.api.YTDLPHandler'):
                with patch('youtube_toolkit.api.YouTubeAPIHandler'):
                    from youtube_toolkit import YouTubeToolkit
                    toolkit = YouTubeToolkit()
                    toolkit.pytubefix = mock_handler

                    result = toolkit.get.chapters("https://youtube.com/watch?v=test")

                    assert len(result) == 3
                    assert result[0]['title'] == 'Introduction'

    def test_search_with_filters(self):
        """Test search_with_filters delegates to pytubefix.advanced_search."""
        with patch('youtube_toolkit.api.PyTubeFixHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.advanced_search.return_value = {
                'videos': [],
                'query': 'test',
                'filters_applied': {'duration': 'medium'}
            }
            mock_handler_cls.return_value = mock_handler

            with patch('youtube_toolkit.api.YTDLPHandler'):
                with patch('youtube_toolkit.api.YouTubeAPIHandler'):
                    from youtube_toolkit import YouTubeToolkit
                    toolkit = YouTubeToolkit()
                    toolkit.pytubefix = mock_handler

                    result = toolkit.search.with_filters(
                        "python",
                        duration='medium',
                        upload_date='month'
                    )

                    mock_handler.advanced_search.assert_called_once_with(
                        query="python",
                        duration='medium',
                        upload_date='month',
                        sort_by=None,
                        features=None,
                        result_type='video',
                        max_results=20
                    )

    def test_get_playlist_info(self, sample_playlist_info):
        """Test get_playlist_info delegates to pytubefix."""
        with patch('youtube_toolkit.api.PyTubeFixHandler') as mock_handler_cls:
            mock_handler = MagicMock()
            mock_handler.get_playlist_info.return_value = sample_playlist_info
            mock_handler_cls.return_value = mock_handler

            with patch('youtube_toolkit.api.YTDLPHandler'):
                with patch('youtube_toolkit.api.YouTubeAPIHandler'):
                    from youtube_toolkit import YouTubeToolkit
                    toolkit = YouTubeToolkit()
                    toolkit.pytubefix = mock_handler

                    result = toolkit.get.playlist("https://youtube.com/playlist?list=PLxxxxxxx")

                    assert result['title'] == 'Python Tutorials'
                    assert result['video_count'] == 50


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in channel features."""

    def test_get_channel_videos_handles_import_error(self):
        """Test get_channel_videos handles pytubefix import error."""
        from youtube_toolkit.handlers.pytubefix_handler import PyTubeFixHandler
        handler = PyTubeFixHandler()
        handler._initialized = False

        with patch.object(handler, '_ensure_initialized', side_effect=ImportError("pytubefix not found")):
            with pytest.raises(ImportError):
                handler.get_channel_videos("@Fireship")

    def test_scrapetube_handler_raises_when_not_installed(self):
        """Test ScrapeTubeHandler raises ImportError when scrapetube not installed."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()
        handler._initialized = True
        handler._available = False

        with pytest.raises(ImportError, match="scrapetube is not installed"):
            handler._ensure_initialized()

    def test_parse_video_result_handles_empty_dict(self):
        """Test _parse_video_result handles empty dict gracefully."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        result = handler._parse_video_result({})

        # Empty dict should still return a dict with empty/default values
        assert isinstance(result, dict)
        assert result.get('video_id', '') == ''
        assert result.get('title', '') == ''

    def test_parse_video_result_handles_none(self):
        """Test _parse_video_result handles None gracefully."""
        from youtube_toolkit.handlers.scrapetube_handler import ScrapeTubeHandler
        handler = ScrapeTubeHandler()

        result = handler._parse_video_result(None)

        assert result == {}
