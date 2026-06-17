"""
Tests for Phase 5 parallel / async download features.

Covers the three additive axes plus the thread-safety prerequisite, all with
mocks (no network):
  - axis ①: concurrent_fragments -> yt-dlp's concurrent_fragment_downloads option
  - axis ②: download_many fan-out (parallel vs sequential, order, error isolation)
  - axis ③: async wrappers (audio_async / video_async / many_async)
  - 5.0: @rate_limit is thread-safe under concurrent callers
  - backward-compat: new params are all trailing + defaulted; old calls unchanged
"""

import asyncio
import inspect
import threading
import time
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from youtube_toolkit.handlers.yt_dlp_handler import YTDLPHandler
from youtube_toolkit.services.download import DownloadService
from youtube_toolkit.sub_apis import DownloadAPI
from youtube_toolkit.utils.request_interceptor import rate_limit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextmanager
def _mock_ydl(handler):
    """Mock handler._ydl.YoutubeDL, capturing every ydl_opts dict passed in.

    Yields the list of captured opts (copies, since the handler mutates the
    same dict across format-selector retries).
    """
    captured = []

    class _FakeYDL:
        def __init__(self, opts):
            captured.append(dict(opts))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, urls):
            return 0

    handler._initialized = True
    handler._ydl = MagicMock()
    handler._ydl.YoutubeDL = _FakeYDL
    yield captured


# ---------------------------------------------------------------------------
# Axis ① — concurrent_fragments -> yt-dlp concurrent_fragment_downloads
# ---------------------------------------------------------------------------

class TestAxisOneConcurrentFragments:
    def test_concurrent_fragments_passed_to_ydl_opts(self, tmp_path):
        handler = YTDLPHandler()
        with _mock_ydl(handler) as captured:
            # Make the post-download file lookup succeed on first attempt.
            audio_file = tmp_path / "dQw4w9WgXcQ.wav"
            audio_file.write_bytes(b"x" * 16)
            handler.download_audio(
                "dQw4w9WgXcQ",
                output_path=str(tmp_path),
                format="wav",
                progress_callback=False,
                concurrent_fragments=4,
            )
        assert captured, "YoutubeDL was never constructed"
        assert captured[0].get("concurrent_fragment_downloads") == 4

    def test_default_omits_concurrent_fragment_downloads(self, tmp_path):
        handler = YTDLPHandler()
        with _mock_ydl(handler) as captured:
            audio_file = tmp_path / "dQw4w9WgXcQ.wav"
            audio_file.write_bytes(b"x" * 16)
            handler.download_audio(
                "dQw4w9WgXcQ",
                output_path=str(tmp_path),
                format="wav",
                progress_callback=False,
            )
        assert captured
        # Default (concurrent_fragments=1) must NOT add the key -> behaviour unchanged.
        assert "concurrent_fragment_downloads" not in captured[0]

    def test_video_concurrent_fragments_passed(self, tmp_path):
        handler = YTDLPHandler()
        with _mock_ydl(handler) as captured:
            video_file = tmp_path / "dQw4w9WgXcQ.mp4"
            video_file.write_bytes(b"x" * 16)
            handler.download_video(
                "dQw4w9WgXcQ",
                output_path=str(tmp_path),
                quality="720p",
                progress_callback=False,
                concurrent_fragments=8,
            )
        assert captured
        assert captured[0].get("concurrent_fragment_downloads") == 8


# ---------------------------------------------------------------------------
# Axis ② — download_many fan-out
# ---------------------------------------------------------------------------

def _make_service(download_audio_impl):
    """Build a DownloadService whose toolkit.download_audio is mocked."""
    toolkit = MagicMock()
    toolkit.download_audio.side_effect = download_audio_impl
    return DownloadService(toolkit)


class TestAxisTwoDownloadMany:
    def test_parallel_calls_all_and_preserves_order(self):
        call_lock = threading.Lock()
        calls = []

        def fake_audio(url, **kwargs):
            with call_lock:
                calls.append(url)
            time.sleep(0.05)
            return f"/out/{url}.wav"

        service = _make_service(fake_audio)
        urls = [f"u{i}" for i in range(6)]
        results = service.download_many(urls, media_type="audio", max_workers=4)

        # All called.
        assert sorted(calls) == sorted(urls)
        # Results aligned to input order.
        assert [r["url"] for r in results] == urls
        assert all(r["success"] for r in results)
        assert [r["path"] for r in results] == [f"/out/{u}.wav" for u in urls]

    def test_single_failure_does_not_abort_others(self):
        def fake_audio(url, **kwargs):
            if url == "bad":
                raise RuntimeError("boom")
            return f"/out/{url}.wav"

        service = _make_service(fake_audio)
        urls = ["a", "bad", "c"]
        results = service.download_many(urls, media_type="audio", max_workers=3)

        assert [r["url"] for r in results] == urls
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert results[1]["path"] is None
        assert "boom" in results[1]["error"]
        assert results[2]["success"] is True

    def test_sequential_when_max_workers_one(self):
        order = []

        def fake_audio(url, **kwargs):
            order.append(url)
            return f"/out/{url}.wav"

        service = _make_service(fake_audio)
        urls = ["a", "b", "c"]
        results = service.download_many(urls, media_type="audio", max_workers=1)

        # Sequential path preserves call order exactly.
        assert order == urls
        assert [r["url"] for r in results] == urls
        assert all(r["success"] for r in results)

    def test_video_media_type_routes_to_download_video(self):
        toolkit = MagicMock()
        toolkit.download_video.side_effect = lambda url, **kw: f"/v/{url}.mp4"
        service = DownloadService(toolkit)
        results = service.download_many(["a", "b"], media_type="video",
                                        quality="1080p", max_workers=2)
        assert all(r["success"] for r in results)
        assert {r["path"] for r in results} == {"/v/a.mp4", "/v/b.mp4"}
        toolkit.download_video.assert_called()


# ---------------------------------------------------------------------------
# 5.0 — rate_limit thread-safety
# ---------------------------------------------------------------------------

class TestRateLimitThreadSafe:
    def test_concurrent_calls_do_not_corrupt_state(self):
        class Dummy:
            @rate_limit(max_requests=10_000, window_minutes=60)
            def ping(self):
                return "ok"

        d = Dummy()
        n_threads = 20
        per_thread = 25
        errors = []

        def worker():
            try:
                for _ in range(per_thread):
                    d.ping()
            except Exception as e:  # pragma: no cover - failure path
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        rate_data = Dummy.ping._rate_limit_data
        # Every call recorded exactly once; no lost/duplicated appends.
        assert len(rate_data["requests"]) == n_threads * per_thread


# ---------------------------------------------------------------------------
# Axis ③ — async wrappers
# ---------------------------------------------------------------------------

class TestAxisThreeAsync:
    def test_audio_async_matches_sync(self):
        toolkit = MagicMock()
        api = DownloadAPI(toolkit)
        with patch.object(api, "audio", return_value="/out/a.wav") as m:
            result = asyncio.run(api.audio_async("u", format="mp3"))
        assert result == "/out/a.wav"
        m.assert_called_once_with("u", format="mp3")

    def test_video_async_matches_sync(self):
        toolkit = MagicMock()
        api = DownloadAPI(toolkit)
        with patch.object(api, "video", return_value="/out/v.mp4") as m:
            result = asyncio.run(api.video_async("u", quality="720p"))
        assert result == "/out/v.mp4"
        m.assert_called_once_with("u", quality="720p")

    def test_many_async_matches_sync(self):
        toolkit = MagicMock()
        api = DownloadAPI(toolkit)
        expected = [{"url": "u", "success": True, "path": "/p", "error": None}]
        with patch.object(api, "many", return_value=expected) as m:
            result = asyncio.run(api.many_async(["u"], max_workers=2))
        assert result == expected
        m.assert_called_once_with(["u"], max_workers=2)


# ---------------------------------------------------------------------------
# Backward compatibility — signatures
# ---------------------------------------------------------------------------

class TestBackwardCompatSignatures:
    def _params(self, func):
        return list(inspect.signature(func).parameters.values())

    def test_download_audio_new_param_trailing_defaulted(self):
        params = self._params(DownloadService.download_audio)
        names = [p.name for p in params]
        # Old params keep their order/position.
        assert names[:7] == [
            "self", "url", "format", "progress_callback",
            "prefer_yt_dlp", "output_path", "bitrate",
        ]
        # New param is last and defaulted.
        assert names[-1] == "concurrent_fragments"
        assert params[-1].default == 1

    def test_download_video_new_param_trailing_defaulted(self):
        params = self._params(DownloadService.download_video)
        names = [p.name for p in params]
        assert names[:6] == [
            "self", "url", "quality", "progress_callback",
            "prefer_yt_dlp", "output_path",
        ]
        assert names[-1] == "concurrent_fragments"
        assert params[-1].default == 1

    def test_download_playlist_media_new_param_trailing_defaulted(self):
        from youtube_toolkit.services.playlist import PlaylistService
        params = self._params(PlaylistService.download_playlist_media)
        names = [p.name for p in params]
        assert names[:7] == [
            "self", "playlist_url", "media_type", "format",
            "quality", "include_captions", "audio_bitrate",
        ]
        assert names[-1] == "max_workers"
        assert params[-1].default == 1

    def test_download_many_signature(self):
        params = inspect.signature(DownloadService.download_many).parameters
        assert params["media_type"].default == "audio"
        assert params["max_workers"].default == 1
        # keyword-only after urls
        assert params["max_workers"].kind == inspect.Parameter.KEYWORD_ONLY

    def test_old_call_style_unchanged(self):
        """Calling without any new params behaves exactly as before."""
        toolkit = MagicMock()
        toolkit.download_audio.return_value = "/out/a.wav"
        service = DownloadService(toolkit)
        # Sequential (default) download_many with positional-style kwargs only.
        results = service.download_many(["u"], media_type="audio")
        assert results == [
            {"url": "u", "success": True, "path": "/out/a.wav", "error": None}
        ]
