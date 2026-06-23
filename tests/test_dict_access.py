"""
Tests for DictAccessMixin applied to result dataclasses.

Verifies that each result dataclass that inherits DictAccessMixin supports both
attribute access (``obj.x``) and read-only dict-style access (``obj['x']``,
``obj.get('x')``, ``'x' in obj``, ``dict(obj)``), and that a missing key raises
KeyError.
"""

import pytest

from youtube_toolkit.core.dict_access import DictAccessMixin
from youtube_toolkit.core.video_info import VideoInfo
from youtube_toolkit.core.download import DownloadResult
from youtube_toolkit.core.search import SearchResult, SearchResultItem
from youtube_toolkit.core.comments import CommentResult
from youtube_toolkit.core.captions import CaptionResult


def _make_video_info():
    return VideoInfo(
        title="Test Title",
        duration=120,
        views=1000,
        author="Test Author",
        video_id="abc123",
        url="https://youtu.be/abc123",
    )


def _make_download_result():
    return DownloadResult(
        file_path="/tmp/file.mp3",
        success=True,
        file_size=2048,
        format="mp3",
    )


def _make_search_result():
    item = SearchResultItem(
        kind="youtube#video",
        etag="etag1",
        video_id="vid1",
        title="Item Title",
    )
    return SearchResult(items=[item], total_results=1, query="test query")


def _make_comment_result():
    return CommentResult(total_results=5)


def _make_caption_result():
    return CaptionResult()


# (instance_factory, an existing attribute name, expected value or sentinel)
CASES = [
    ("VideoInfo", _make_video_info, "title", "Test Title"),
    ("DownloadResult", _make_download_result, "file_path", "/tmp/file.mp3"),
    ("SearchResult", _make_search_result, "query", "test query"),
    ("CommentResult", _make_comment_result, "total_results", 5),
    ("CaptionResult", _make_caption_result, "quota_cost", 50),
]


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_is_dict_access_mixin(name, factory, key, expected):
    obj = factory()
    assert isinstance(obj, DictAccessMixin), f"{name} should inherit DictAccessMixin"


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_attr_and_item_access_match(name, factory, key, expected):
    obj = factory()
    assert getattr(obj, key) == expected
    assert obj[key] == expected
    assert obj[key] == getattr(obj, key)


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_get_method(name, factory, key, expected):
    obj = factory()
    assert obj.get(key) == expected
    assert obj.get("definitely_missing_key") is None
    assert obj.get("definitely_missing_key", "default") == "default"


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_contains(name, factory, key, expected):
    obj = factory()
    assert key in obj
    assert "definitely_missing_key" not in obj


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_dict_conversion(name, factory, key, expected):
    obj = factory()
    as_dict = dict(obj)
    assert isinstance(as_dict, dict)
    # dict(obj) draws keys from to_dict() but values via attribute access, so the
    # key set matches to_dict() even though nested values stay as live objects.
    assert set(as_dict.keys()) == set(obj.to_dict().keys())
    assert key in as_dict
    assert as_dict[key] == getattr(obj, key)


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_missing_key_raises_keyerror(name, factory, key, expected):
    obj = factory()
    with pytest.raises(KeyError):
        _ = obj["definitely_missing_key"]


@pytest.mark.parametrize("name,factory,key,expected", CASES)
def test_iter_and_keys(name, factory, key, expected):
    obj = factory()
    keys_from_iter = list(iter(obj))
    keys_from_keys = list(obj.keys())
    assert keys_from_iter == keys_from_keys
    assert list(obj.to_dict().keys()) == keys_from_keys
