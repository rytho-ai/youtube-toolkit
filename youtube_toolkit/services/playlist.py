"""
playlist.py — playlist-domain service.

Holds playlist URL listing, info, filtering, and bulk media download logic
descended out of YouTubeToolkit (api.py). api.py keeps one-line delegations;
bodies are verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit.
"""

from typing import List, Dict, Any


class PlaylistService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_playlist_urls(self, playlist_url: str) -> List[str]:
        import time

        # Try YouTube API first (most reliable)
        try:
            urls = self._toolkit.youtube_api.get_playlist_urls(playlist_url)
            if urls:
                return urls
        except Exception as e:
            print(f"YouTube API playlist failed: {e}")

        # Try PyTubeFix second
        try:
            urls = self._toolkit.pytubefix.get_playlist_urls(playlist_url)
            if urls:
                return urls
        except Exception as e:
            print(f"PyTubeFix playlist failed: {e}")

        # Try YT-DLP last
        try:
            urls = self._toolkit.yt_dlp.get_playlist_urls(playlist_url)
            if urls:
                return urls
        except Exception as e:
            print(f"YT-DLP playlist failed: {e}")

        print("❌ All playlist methods failed")
        return []

    def download_playlist_media(self, playlist_url: str, media_type: str = 'audio',
                               format: str = 'wav', quality: str = 'best',
                               include_captions: bool = False, audio_bitrate: str = '128k') -> Dict[str, Any]:
        import json
        import os
        import time
        from datetime import datetime

        # Get playlist info and URLs
        try:
            playlist_info = self._toolkit.youtube_api.get_playlist_info(playlist_url)
        except:
            playlist_info = {
                'title': 'YouTube Playlist',
                'description': 'Playlist downloaded with YouTube Toolkit'
            }

        urls = self._toolkit.get_playlist_urls(playlist_url)
        if not urls:
            return {'success': False, 'error': 'No videos found in playlist'}

        # Create folder structure
        base_dir = os.path.join(os.getcwd(), 'playlist_downloads')
        playlist_dir = os.path.join(base_dir, self._toolkit._sanitize_filename(playlist_info['title']))

        folders = {
            'base': playlist_dir,
            'audio': os.path.join(playlist_dir, 'audio'),
            'video': os.path.join(playlist_dir, 'video'),
            'captions': os.path.join(playlist_dir, 'captions')
        }

        # Create directories
        for folder in folders.values():
            os.makedirs(folder, exist_ok=True)

        # Initialize metadata
        metadata = {
            'playlist_info': {
                'title': playlist_info['title'],
                'description': playlist_info.get('description', ''),
                'video_count': len(urls),
                'playlist_url': playlist_url,
                'download_date': datetime.now().isoformat(),
                'download_settings': {
                    'media_type': media_type,
                    'format': format,
                    'quality': quality,
                    'include_captions': include_captions
                }
            },
            'videos': [],
            'download_summary': {
                'total_videos': len(urls),
                'successful_downloads': 0,
                'failed_downloads': 0,
                'total_size_mb': 0,
                'download_time_seconds': 0
            }
        }

        start_time = time.time()

        # Download each video into metadata
        self._download_playlist_videos(
            urls, media_type, format, quality, include_captions, audio_bitrate,
            folders, playlist_dir, metadata
        )

        # Finalize statistics, persist metadata and print summary
        metadata_path = self._finalize_playlist_download(
            metadata, playlist_dir, urls, start_time
        )

        return {
            'success': True,
            'playlist_dir': playlist_dir,
            'metadata_path': metadata_path,
            'metadata': metadata
        }

    def _download_playlist_videos(self, urls, media_type, format, quality,
                                  include_captions, audio_bitrate,
                                  folders, playlist_dir, metadata):
        """Download each playlist video, appending per-video metadata + counts.

        Mutates ``metadata`` in place (videos list and download_summary counters).
        """
        import os

        # Download each video
        for i, url in enumerate(urls, 1):
            try:
                print(f"📥 [{i}/{len(urls)}] Processing...")

                # Get video info
                video_info = self._toolkit.get_video_info(url)
                video_title = self._toolkit._sanitize_filename(video_info['title'])

                # Download main media
                if media_type == 'audio':
                    media_path = self._toolkit.download_audio(
                        url,
                        format=format,
                        output_path=os.path.join(folders['audio'], f"{video_title}.{format}"),
                        bitrate=audio_bitrate
                    )
                else:  # video
                    media_path = self._toolkit.download_video(
                        url,
                        quality=quality,
                        output_path=os.path.join(folders['video'], f"{video_title}.mp4")
                    )

                # Download captions if requested
                caption_path = None
                if include_captions:
                    try:
                        caption_path = self._toolkit.download_captions(
                            url,
                            language_code='en',
                            output_path=os.path.join(folders['captions'], f"{video_title}_en.txt")
                        )
                    except Exception as e:
                        print(f"⚠️  Captions failed: {e}")
                        # Continue without captions rather than failing the whole download

                # Update metadata
                video_metadata = {
                    'index': i,
                    'video_id': video_info.get('video_id', ''),
                    'title': video_info['title'],
                    'channel': video_info.get('channel', 'Unknown'),
                    'duration': video_info.get('duration', 0),
                    'views': video_info.get('view_count', 0),
                    'upload_date': video_info.get('upload_date', ''),
                    'download_status': 'success',
                    'files': {
                        'audio': os.path.relpath(media_path, playlist_dir) if media_type == 'audio' else None,
                        'video': os.path.relpath(media_path, playlist_dir) if media_type == 'video' else None,
                        'caption': os.path.relpath(caption_path, playlist_dir) if caption_path else None
                    },
                    'error': None
                }

                metadata['videos'].append(video_metadata)
                metadata['download_summary']['successful_downloads'] += 1

                print(f"✅ Downloaded: {video_title}")

            except Exception as e:
                error_msg = f"Video {i} failed: {e}"
                print(f"❌ {error_msg}")

                # Add failed video to metadata
                video_metadata = {
                    'index': i,
                    'video_id': self._toolkit.extract_video_id(url),
                    'title': f"Video {i}",
                    'channel': 'Unknown',
                    'duration': 0,
                    'views': 0,
                    'upload_date': '',
                    'download_status': 'failed',
                    'files': {'audio': None, 'video': None, 'caption': None},
                    'error': str(e)
                }

                metadata['videos'].append(video_metadata)
                metadata['download_summary']['failed_downloads'] += 1

    def _finalize_playlist_download(self, metadata, playlist_dir, urls, start_time):
        """Compute final stats, write metadata.json, print summary.

        Returns the path to the written metadata file.
        """
        import json
        import os
        import time

        # Calculate final statistics
        end_time = time.time()
        metadata['download_summary']['download_time_seconds'] = end_time - start_time

        # Calculate total size
        total_size = 0
        for video in metadata['videos']:
            if video['download_status'] == 'success':
                for file_path in video['files'].values():
                    if file_path and os.path.exists(os.path.join(playlist_dir, file_path)):
                        total_size += os.path.getsize(os.path.join(playlist_dir, file_path))

        metadata['download_summary']['total_size_mb'] = round(total_size / (1024 * 1024), 2)

        # Save metadata
        metadata_path = os.path.join(playlist_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Print summary
        print(f"\n🎯 Playlist download complete!")
        print(f"   📁 Saved to: {playlist_dir}")
        print(f"   📊 Metadata: {metadata_path}")
        print(f"   ✅ Successful: {metadata['download_summary']['successful_downloads']}/{len(urls)}")
        print(f"   ❌ Failed: {metadata['download_summary']['failed_downloads']}")
        print(f"   💾 Total size: {metadata['download_summary']['total_size_mb']} MB")
        print(f"   ⏱️  Time: {metadata['download_summary']['download_time_seconds']:.1f} seconds")

        return metadata_path

    def get_playlist_info(self, playlist_url: str) -> Dict[str, Any]:
        return self._toolkit.pytubefix.get_playlist_info(playlist_url)

    def filter_playlist(self, playlist_url: str, match_filter: str = None,
                        date_range: tuple = None,
                        min_views: int = None,
                        max_views: int = None,
                        min_duration: int = None,
                        max_duration: int = None,
                        title_contains: str = None,
                        title_not_contains: str = None) -> List[Dict[str, Any]]:
        return self._toolkit.yt_dlp.filter_playlist(
            playlist_url, match_filter, date_range,
            min_views, max_views, min_duration, max_duration,
            title_contains, title_not_contains
        )

    def playlist(self, url: str) -> List[str]:
        return self._toolkit.get_playlist_urls(url)

    def get_playlist_urls_pytubefix(self, url: str) -> List[str]:
        return self._toolkit.pytubefix.get_playlist_urls(url)
