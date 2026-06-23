"""
system.py — diagnostics / capability-listing service.

Holds handler self-tests and static capability lists (supported languages /
regions) descended out of YouTubeToolkit (api.py). api.py keeps one-line
delegations; bodies here are verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit.
"""

from typing import List, Dict, Any


class SystemService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def test_handlers(self, url: str) -> Dict[str, bool]:
        results = {}

        # Test pytubefix
        try:
            results['pytubefix'] = self._toolkit.pytubefix.test_connection(url)
        except:
            results['pytubefix'] = False

        # Test yt-dlp
        try:
            results['yt_dlp'] = self._toolkit.yt_dlp.test_connection(url)
        except:
            results['yt_dlp'] = False

        # Test YouTube API
        try:
            results['youtube_api'] = self._toolkit.youtube_api.test_connection(url)
        except:
            results['youtube_api'] = False

        return results

    def get_anti_detection_status(self) -> Dict[str, Any]:
        """Get comprehensive anti-detection status."""
        return {
            'global_status': self._toolkit.anti_detection.get_status(),
            'handlers': {
                'pytubefix': self._toolkit.pytubefix.get_anti_detection_status(),
                'yt_dlp': self._toolkit.yt_dlp.get_anti_detection_status(),
                'youtube_api': {
                    'note': 'Official API - no anti-detection needed',
                    'status': 'active'
                }
            }
        }

    def test_anti_detection(self, url: str) -> Dict[str, Any]:
        """Test anti-detection system with a simple request."""
        import time

        try:
            print("🧪 Testing anti-detection system...")

            # Test each handler with anti-detection
            results = {}

            # Test PyTubeFix
            print("  Testing PyTubeFix...")
            start_time = time.time()
            info = self._toolkit.pytubefix.get_video_info(url)
            pytubefix_time = time.time() - start_time
            results['pytubefix'] = {
                'success': info is not None,
                'time_taken': pytubefix_time,
                'anti_detection_status': self._toolkit.pytubefix.get_anti_detection_status()
            }

            # Test YT-DLP
            print("  Testing YT-DLP...")
            start_time = time.time()
            info = self._toolkit.yt_dlp.get_video_info(url)
            ytdlp_time = time.time() - start_time
            results['yt_dlp'] = {
                'success': info is not None,
                'time_taken': ytdlp_time,
                'anti_detection_status': self._toolkit.yt_dlp.get_anti_detection_status()
            }

            # Test YouTube API
            print("  Testing YouTube API...")
            start_time = time.time()
            metadata = self._toolkit.youtube_api.fetch_metadata(url)
            api_time = time.time() - start_time
            results['youtube_api'] = {
                'success': 'error' not in metadata,
                'time_taken': api_time,
                'note': 'Official API - no anti-detection needed'
            }

            # Overall status
            results['overall'] = {
                'all_successful': all(r['success'] for r in results.values() if isinstance(r, dict) and 'success' in r),
                'total_time': sum(r['time_taken'] for r in results.values() if isinstance(r, dict) and 'time_taken' in r),
                'global_anti_detection': self._toolkit.anti_detection.get_status()
            }

            print("✅ Anti-detection test completed!")
            return results

        except Exception as e:
            print(f"❌ Anti-detection test failed: {e}")
            return {'error': str(e)}

    def test_search(self, query: str = "test") -> Dict[str, Any]:
        """
        Test search functionality across all handlers.
        """
        print(f"🔍 Testing search functionality with query: '{query}'")

        results = {}

        # Test PyTubeFix search
        try:
            pytube_results = self._toolkit.pytubefix.search_videos(query, max_results=3)
            results['pytubefix'] = {
                'success': True,
                'count': len(pytube_results),
                'sample': pytube_results[0] if pytube_results else None
            }
            print(f"✅ PyTubeFix: {len(pytube_results)} results")
        except Exception as e:
            results['pytubefix'] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ PyTubeFix: {e}")

        # Test YouTube API search
        try:
            api_results = self._toolkit.youtube_api.search_videos(query, max_results=3)
            results['youtube_api'] = {
                'success': True,
                'count': len(api_results),
                'sample': api_results[0] if api_results else None
            }
            print(f"✅ YouTube API: {len(api_results)} results")
        except Exception as e:
            results['youtube_api'] = {
                'success': False,
                'error': str(e)
            }
            print(f"❌ YouTube API: {e}")

        # Overall status
        working_handlers = sum(1 for r in results.values() if r.get('success', False))
        results['overall'] = {
            'working_handlers': working_handlers,
            'total_handlers': len(results),
            'all_working': working_handlers == len(results)
        }

        print(f"🎯 Search test completed: {working_handlers}/{len(results)} handlers working")
        return results

    def get_supported_languages(self, language: str = 'en') -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_supported_languages(language)

    def get_supported_regions(self, language: str = 'en') -> List[Dict[str, Any]]:
        return self._toolkit.youtube_api.get_supported_regions(language)
