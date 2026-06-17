"""
download.py — download/export-domain service.

Holds audio/video/short/live downloads (with handler fallback), filtered &
batch downloads, metadata/thumbnail/subtitle export, sponsorblock/archive
downloads, and the clean-API DownloadResult builder, descended out of
YouTubeToolkit (api.py). api.py keeps one-line delegations; bodies are
verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.core.download.DownloadResult.
"""

import os
import time
from typing import Optional, List, Dict, Any
from ..core.download import DownloadResult


class DownloadService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def download_audio(self, url: str, format: str = 'wav',
                       progress_callback: bool = True, prefer_yt_dlp: bool = False,
                       output_path: str = None, bitrate: str = '128k') -> str:
        video_id = self._toolkit.extract_video_id(url)

        # Standardize default output path for consistent behavior
        if output_path is None:
            # Get video title for consistent naming
            try:
                # Try to get title from pytubefix first
                yt = self._toolkit.pytubefix._yt(url)
                title = self._toolkit.pytubefix.sanitize_path(yt.title.replace(' ', '-'))
            except:
                # Fallback to video ID if title extraction fails
                title = video_id

            # Create consistent default path in current working directory
            default_path = os.path.join(os.getcwd(), f'{title}.{format}')

            # For pytubefix: use full path, for yt-dlp: use directory only
            pytubefix_path = default_path
            ytdlp_path = os.path.dirname(default_path)
        else:
            pytubefix_path = output_path
            ytdlp_path = output_path

        if prefer_yt_dlp:
            # Try yt-dlp first
            try:
                return self._toolkit.yt_dlp.download_audio(video_id, output_path=ytdlp_path, format=format, progress_callback=progress_callback, bitrate=bitrate)
            except Exception as e:
                print(f"YT-DLP audio download failed: {e}")
                # Fallback to pytubefix
                return self._toolkit.pytubefix.download_audio(url, output_path=pytubefix_path, format=format, progress_callback=progress_callback, bitrate=bitrate)
        else:
            # Try pytubefix first
            try:
                return self._toolkit.pytubefix.download_audio(url, output_path=pytubefix_path, format=format, progress_callback=progress_callback, bitrate=bitrate)
            except Exception as e:
                print(f"PyTubeFix audio download failed: {e}")
                # Fallback to yt-dlp
                return self._toolkit.yt_dlp.download_audio(video_id, output_path=ytdlp_path, format=format, progress_callback=progress_callback, bitrate=bitrate)

    def download_video(self, url: str, quality: str = 'best',
                       progress_callback: bool = True, prefer_yt_dlp: bool = True,
                       output_path: str = None) -> str:
        video_id = self._toolkit.extract_video_id(url)

        # Standardize default output path for consistent behavior
        if output_path is None:
            # Get video title for consistent naming
            try:
                # Try to get title from pytubefix first
                yt = self._toolkit.pytubefix._yt(url)
                title = self._toolkit.pytubefix.sanitize_path(yt.title.replace(' ', '-'))
            except:
                # Fallback to video ID if title extraction fails
                title = video_id

            # Create consistent default path in current working directory
            default_path = os.path.join(os.getcwd(), f'{title}.mp4')

            # For pytubefix: use full path, for yt-dlp: use directory only
            pytubefix_path = default_path
            ytdlp_path = os.path.dirname(default_path)
        else:
            pytubefix_path = output_path
            ytdlp_path = output_path

        # Use verbose setting to control progress display
        effective_progress = progress_callback and self._toolkit.verbose

        if prefer_yt_dlp:
            # Try yt-dlp first
            try:
                if self._toolkit.verbose:
                    print("🎯 Trying YT-DLP first...")
                return self._toolkit.yt_dlp.download_video(video_id, output_path=ytdlp_path, quality=quality, progress_callback=effective_progress)
            except Exception as e:
                if self._toolkit.verbose:
                    print(f"YT-DLP video download failed: {e}")
                    print("🔄 Falling back to PyTubeFix...")
                # Fallback to pytubefix
                return self._toolkit.pytubefix.download_video(url, output_path=pytubefix_path, quality=quality, progress_callback=effective_progress)
        else:
            # Try pytubefix first
            try:
                if self._toolkit.verbose:
                    print("🎯 Trying PyTubeFix first (best quality)...")
                return self._toolkit.pytubefix.download_video(url, output_path=pytubefix_path, quality=quality, progress_callback=effective_progress)
            except Exception as e:
                if self._toolkit.verbose:
                    print(f"PyTubeFix video download failed: {e}")
                    print("🔄 Falling back to YT-DLP...")
                # Fallback to yt-dlp
                return self._toolkit.yt_dlp.download_video(video_id, output_path=ytdlp_path, quality=quality, progress_callback=effective_progress)

    def download(self, url: str, type: str = 'audio', format: str = 'wav',
                 quality: str = 'best', output_path: Optional[str] = None,
                 bitrate: str = '128k', progress: bool = True) -> DownloadResult:
        start_time = time.time()
        backend_used = None

        try:
            if type == 'audio':
                file_path = self._toolkit.download_audio(
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
                file_path = self._toolkit.download_video(
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

    def download_with_sponsorblock(self, url: str, output_path: str = None,
                                   action: str = 'remove',
                                   categories: List[str] = None) -> str:
        return self._toolkit.yt_dlp.download_with_sponsorblock(url, output_path, action, categories)

    def download_live_stream(self, url: str, output_path: str = None,
                             from_start: bool = False,
                             duration: int = None) -> str:
        return self._toolkit.yt_dlp.download_live_stream(url, output_path, from_start, duration)

    def download_with_archive(self, url: str, output_path: str = None,
                              archive_file: str = None,
                              format: str = 'best') -> Optional[str]:
        return self._toolkit.yt_dlp.download_with_archive(url, output_path, archive_file, format)

    def is_in_archive(self, url: str, archive_file: str) -> bool:
        return self._toolkit.yt_dlp.is_in_archive(url, archive_file)

    def download_subtitles(self, url: str, lang: str = 'en',
                           output_path: str = None) -> str:
        return self._toolkit.yt_dlp.download_captions(url, lang, output_path)

    def convert_subtitles(self, input_path: str, output_format: str = 'srt') -> str:
        return self._toolkit.yt_dlp.convert_subtitles(input_path, output_format)

    def get_supported_subtitle_formats(self) -> List[str]:
        return ['srt', 'vtt', 'ass', 'json3', 'ttml']

    def split_by_chapters(self, url: str, output_path: str = None,
                          format: str = 'mp4') -> List[str]:
        return self._toolkit.yt_dlp.split_by_chapters(url, output_path, format)

    def download_thumbnail(self, url: str, output_path: str = None,
                           quality: str = 'best') -> str:
        return self._toolkit.yt_dlp.download_thumbnail(url, output_path, quality)

    def download_audio_with_metadata(self, url: str, output_path: str = None,
                                     format: str = 'mp3',
                                     embed_thumbnail: bool = True,
                                     add_metadata: bool = True) -> str:
        return self._toolkit.yt_dlp.download_audio_with_metadata(
            url, output_path, format, embed_thumbnail, add_metadata
        )

    def download_with_filter(self, url: str, output_path: str = None,
                             match_filter: str = None,
                             format: str = 'best') -> Optional[str]:
        return self._toolkit.yt_dlp.download_with_filter(url, output_path, match_filter, format)

    def get_videos_matching_filter(self, url: str, match_filter: str = None,
                                   max_results: int = None) -> List[Dict[str, Any]]:
        return self._toolkit.yt_dlp.get_videos_matching_filter(url, match_filter, max_results)

    def batch_download_with_filter(self, url: str, output_path: str = None,
                                   match_filter: str = None,
                                   format: str = 'best',
                                   max_downloads: int = None,
                                   skip_existing: bool = True) -> List[str]:
        return self._toolkit.yt_dlp.batch_download_with_filter(
            url, output_path, match_filter, format, max_downloads, skip_existing
        )

    def download_with_metadata_files(self, url: str, output_path: str = None,
                                     write_info_json: bool = True,
                                     write_description: bool = True,
                                     write_thumbnail: bool = True,
                                     write_subtitles: bool = False,
                                     subtitle_langs: List[str] = None,
                                     format: str = 'best') -> Dict[str, str]:
        return self._toolkit.yt_dlp.download_with_metadata_files(
            url, output_path, write_info_json, write_description,
            write_thumbnail, write_subtitles, subtitle_langs, format
        )

    def export_metadata_only(self, url: str, output_path: str = None,
                             format_type: str = 'json') -> str:
        return self._toolkit.yt_dlp.export_metadata_only(url, output_path, format_type)

    def download_short(self, url: str, output_path: str = None,
                       format: str = 'mp4',
                       with_audio: bool = True) -> str:
        return self._toolkit.yt_dlp.download_short(url, output_path, format, with_audio)

    def batch_download_shorts(self, channel_url: str, output_path: str = None,
                              max_downloads: int = 10,
                              format: str = 'mp4') -> List[str]:
        return self._toolkit.yt_dlp.batch_download_shorts(channel_url, output_path, max_downloads, format)

    def get_supported_browsers(self) -> List[str]:
        return ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave', 'chromium', 'vivaldi']

    def extract_cookies_from_browser(self, browser: str = 'chrome') -> str:
        return self._toolkit.yt_dlp.extract_cookies_from_browser(browser)

    def download_video_with_cookies(self, url: str, output_path: Optional[str] = None,
                                    cookies: Optional[str] = None) -> str:
        return self._toolkit.yt_dlp.download_video(
            url, output_path=output_path, cookies=cookies
        )

    def stream_to_buffer(self, url: str, stream_type: str = 'audio',
                         quality: str = 'best') -> bytes:
        return self._toolkit.pytubefix.stream_to_buffer(url, stream_type, quality)

    def get_filesize_preview(self, url: str) -> Dict[str, Any]:
        return self._toolkit.pytubefix.get_filesize_preview(url)
