"""YT-DLP handler for YouTube Toolkit.

This handler implements video information extraction and media downloading
using the yt-dlp package as a backup to pytubefix.
"""

import os
import re
from typing import Optional, Dict, Any, List
from ..utils.helpers import ensure_directory
from ..utils.anti_detection import AntiDetectionManager
from ..utils.request_interceptor import anti_detection_interceptor, rate_limit


class YTDLPHandler:
    """Handler for YT-DLP package functionality."""
    
    def __init__(self, anti_detection: AntiDetectionManager = None):
        """Initialize the YT-DLP handler."""
        self._ydl = None
        self._initialized = False
        self.anti_detection = anti_detection or AntiDetectionManager()
    
    def _ensure_initialized(self):
        """Ensure yt-dlp is available and initialized."""
        if not self._initialized:
            try:
                import yt_dlp
                self._ydl = yt_dlp
                self._initialized = True
            except ImportError:
                raise ImportError("yt-dlp is not installed. Install with: pip install yt-dlp")
    
    def extract_video_id(self, youtube_link: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            youtube_link: YouTube video URL
            
        Returns:
            Video ID string
        """
        if "watch?v=" in youtube_link:
            video_id = youtube_link.split("watch?v=")[-1]
        elif "youtu.be/" in youtube_link:
            video_id = youtube_link.split("youtu.be/")[-1]
        else:
            return None
        
        # Remove URL parameters if present
        return video_id.split("&")[0]
    
    def is_valid_youtube_url(self, url: str) -> bool:
        """Check if the URL is a valid YouTube URL."""
        youtube_regex = (
            r'(https?://)?(www\.)?'
            r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return bool(re.match(youtube_regex, url))
    
    @anti_detection_interceptor
    @rate_limit(max_requests=5, window_minutes=1)
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information using yt-dlp.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with video details
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }

            # Add cookie support if YOUTUBE_COOKIES_FILE environment variable is set
            cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'video_id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'channel': info.get('uploader', ''),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'video_url': url
                }
        except Exception as e:
            raise RuntimeError(f"Failed to get video info with yt-dlp: {e}")
    
    @anti_detection_interceptor
    @rate_limit(max_requests=3, window_minutes=1)
    def download_audio(self, url: str, output_path: str = None, 
                       format: str = 'wav', progress_callback: bool = True, 
                       bitrate: str = 'best') -> str:
        """
        Download audio from a YouTube video using yt-dlp.
        
        Args:
            url: YouTube video ID or URL
            output_path: Output path for the audio file (directory path for yt-dlp)
            format: Audio format ('wav', 'mp3', 'm4a')
            progress_callback: Whether to show download progress
            bitrate: Audio bitrate ('best', '320k', '256k', '192k', '128k', '96k', '64k')
            
        Returns:
            str: Path to the downloaded audio file
        """
        self._ensure_initialized()
        
        # Extract video ID if full URL is provided
        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url
        
        # Create output directory
        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')
        
        ensure_directory(output_path)
        
        # Map bitrate to yt-dlp format selectors with robust fallbacks
        if bitrate == 'best':
            format_selector = 'bestaudio/best'
        else:
            # Extract numeric bitrate (e.g., '320k' -> 320)
            try:
                bitrate_num = int(bitrate.replace('k', ''))
                # More robust format selector with multiple fallbacks
                format_selector = f'bestaudio[abr<={bitrate_num}]/bestaudio[abr>={bitrate_num}]/bestaudio/best'
            except ValueError:
                # If bitrate format is invalid, use best
                format_selector = 'bestaudio/best'
        
        # Configure postprocessor options based on bitrate
        postprocessor_opts = {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': format,
        }

        # Add bitrate preference to postprocessor if specified
        if bitrate != 'best':
            try:
                bitrate_num = int(bitrate.replace('k', ''))
                postprocessor_opts['preferredquality'] = str(bitrate_num)
            except ValueError:
                pass  # Skip invalid bitrate format

        # Set up yt-dlp options with robust fallbacks
        ydl_opts = {
            'format': format_selector,
            'postprocessors': [postprocessor_opts],
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': not progress_callback,
            'no_warnings': True,
            # Add additional options for better compatibility
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': True,
            'prefer_insecure': False
        }

        # Add cookie support if YOUTUBE_COOKIES_FILE environment variable is set
        cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file

        # Try multiple format selectors if the first one fails
        format_selectors = [
            format_selector,
            'bestaudio/best',
            'bestaudio',
            'best'
        ]

        last_error = None
        for i, current_selector in enumerate(format_selectors):
            try:
                # Update format selector
                ydl_opts['format'] = current_selector

                # If video_id is not a full URL, construct it
                if not self.is_valid_youtube_url(video_id):
                    video_url = f'https://www.youtube.com/watch?v={video_id}'
                else:
                    video_url = video_id

                # Download the audio
                with self._ydl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                # Return the path to the downloaded file
                audio_path = os.path.join(output_path, f'{video_id}.{format}')
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    return audio_path
                else:
                    # Try to find any audio file with the video_id
                    for ext in ['wav', 'mp3', 'm4a', 'webm', 'aac', 'ogg', 'flac']:
                        potential_path = os.path.join(output_path, f'{video_id}.{ext}')
                        if os.path.exists(potential_path) and os.path.getsize(potential_path) > 0:
                            return potential_path

                    # Clean up any empty files
                    for ext in ['wav', 'mp3', 'm4a', 'webm', 'aac', 'ogg', 'flac']:
                        potential_path = os.path.join(output_path, f'{video_id}.{ext}')
                        if os.path.exists(potential_path) and os.path.getsize(potential_path) == 0:
                            os.remove(potential_path)

                    raise ValueError("Audio download failed: file is empty or not found")

            except Exception as e:
                last_error = e
                if i < len(format_selectors) - 1:
                    # Try next format selector
                    continue
                else:
                    # All format selectors failed
                    raise ValueError(f"Failed to download audio with all format selectors. Last error: {e}")
    
    @anti_detection_interceptor
    @rate_limit(max_requests=2, window_minutes=1)
    def download_video(self, url: str, output_path: str = None, 
                       quality: str = 'best', progress_callback: bool = True) -> str:
        """
        Download video from YouTube using yt-dlp.
        
        Args:
            url: YouTube video ID or URL
            output_path: Output path for the video file (directory path for yt-dlp)
            quality: Video quality ('best', 'worst', '720p', '1080p')
            progress_callback: Whether to show download progress
            
        Returns:
            str: Path to the downloaded video file
        """
        self._ensure_initialized()
        
        # Extract video ID if full URL is provided
        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url
        
        # Create output directory
        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')
        
        ensure_directory(output_path)
        
        # Set up yt-dlp options with better format selection and fallback
        if quality == 'best':
            format_spec = 'best[ext=mp4]/best'
        elif quality == '720p':
            # Try 720p, then 1080p, then 480p, then best available
            format_spec = 'best[height<=720][ext=mp4]/best[height<=1080][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best'
        elif quality == '1080p':
            # Try 1080p, then 720p, then 1440p, then best available
            format_spec = 'best[height<=1080][ext=mp4]/best[height<=720][ext=mp4]/best[height<=1440][ext=mp4]/best[ext=mp4]/best'
        elif quality.isdigit():
            # For numeric quality, try exact and then fallback
            format_spec = f'best[height<={quality}][ext=mp4]/best[height<={int(quality)*1.5:.0f}][ext=mp4]/best[ext=mp4]/best'
        else:
            format_spec = 'best[ext=mp4]/best'
        
        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': not progress_callback,
            'no_warnings': True
        }

        # Add cookie support if YOUTUBE_COOKIES_FILE environment variable is set
        cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file

        if progress_callback:
            print(f"   Using format specification: {format_spec}")
            print(f"   Output directory: {output_path}")
        
        try:
            # If video_id is not a full URL, construct it
            if not self.is_valid_youtube_url(video_id):
                video_url = f'https://www.youtube.com/watch?v={video_id}'
            else:
                video_url = video_id
            
            # Try to download with the requested format
            try:
                with self._ydl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
            except Exception as format_error:
                # If the requested format fails, try with a more generic format
                if progress_callback:
                    print(f"Requested format failed, trying fallback format...")
                
                # Try multiple fallback strategies
                fallback_formats = [
                    'best[ext=mp4]/best',
                    'best[height<=720][ext=mp4]/best',
                    'best[height<=480][ext=mp4]/best',
                    'best'
                ]
                
                for fallback_format in fallback_formats:
                    try:
                        if progress_callback:
                            print(f"   Trying fallback format: {fallback_format}")
                        
                        fallback_opts = ydl_opts.copy()
                        fallback_opts['format'] = fallback_format
                        
                        with self._ydl.YoutubeDL(fallback_opts) as ydl:
                            ydl.download([video_url])
                        
                        # If we get here, download succeeded
                        break
                        
                    except Exception as fallback_error:
                        if progress_callback:
                            print(f"   Fallback format {fallback_format} also failed")
                        continue
                else:
                    # If all fallbacks failed, raise the original error
                    raise format_error
            
            # Find the downloaded file (must be non-empty)
            for file in os.listdir(output_path):
                file_path = os.path.join(output_path, file)
                if file.startswith(video_id) and os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                    return file_path

            # Clean up any empty files
            for file in os.listdir(output_path):
                file_path = os.path.join(output_path, file)
                if file.startswith(video_id) and os.path.isfile(file_path) and os.path.getsize(file_path) == 0:
                    os.remove(file_path)

            raise ValueError("Video download failed: file is empty or not found")
        except Exception as e:
            raise ValueError(f"Failed to download video: {e}")
    
    def get_video_description(self, url: str) -> str:
        """
        Get the description of a YouTube video and extract lyrics if present.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Extracted lyrics or description text
        """
        self._ensure_initialized()
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                description = info.get('description', '')
                
                # Try to extract lyrics from description
                lyrics = self.extract_lyrics_from_description(description)
                if lyrics:
                    return lyrics
                
                # Return description if no lyrics found
                return description[:1000] + "..." if len(description) > 1000 else description
                
        except Exception as e:
            raise RuntimeError(f"Failed to get video description: {e}")
    
    def get_available_formats(self, url: str) -> Dict[str, Any]:
        """
        Get available download formats for a video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary of available formats
        """
        self._ensure_initialized()
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                return {
                    'formats': formats,
                    'best': info.get('format_id', ''),
                    'best_audio': info.get('format_id', ''),
                    'best_video': info.get('format_id', '')
                }
        except Exception as e:
            raise RuntimeError(f"Failed to get formats with yt-dlp: {e}")
    
    def test_connection(self, url: str) -> bool:
        """
        Test if yt-dlp can connect to a YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._ensure_initialized()
            ydl_opts = {'quiet': True, 'no_warnings': True}
            
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return bool(info and info.get('id'))
        except Exception:
            return False


    @anti_detection_interceptor
    @rate_limit(max_requests=5, window_minutes=1)
    def get_transcript(self, url: str) -> Optional[str]:
        """
        Get the transcript for a YouTube video using youtube-transcript-api.
        
        Args:
            url: YouTube video URL or ID
            
        Returns:
            Transcript text if available, None otherwise
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Extract video ID if full URL is provided
            video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url
            
            preferred_languages = ['en', 'en-US', 'zh-TW', 'zh-Hant', 'de', 'fr', 'ja', 'ko']
            
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # First try to get a transcript in the preferred languages
            for lang in preferred_languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    transcript_text = ''
                    for entry in transcript.fetch():
                        start = entry['start']
                        duration = entry['duration']
                        text = entry['text']
                        transcript_text += f"[{start}-{start+duration}] {text}\n"
                    return transcript_text.strip()
                except:
                    continue
            
            # If no preferred language is available, get the first available transcript
            for transcript in transcript_list:
                transcript_text = ''
                for entry in transcript.fetch():
                    start = entry['start']
                    duration = entry['duration']
                    text = entry['text']
                    transcript_text += f"[{start}-{start+duration}] {text}\n"
                return transcript_text.strip()
                
        except ImportError:
            print("youtube-transcript-api not installed. Install with: pip install youtube-transcript-api")
            return None
        except Exception as e:
            print(f"Failed to get transcript: {e}")
            return None
    
    def get_lyrics(self, url: str) -> str:
        """
        Extract lyrics from video description or transcript.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Extracted lyrics text
        """
        try:
            # First try to get transcript
            transcript = self.get_transcript(url)
            if transcript:
                return transcript
            
            # Fallback to description
            description = self.get_video_description(url)
            lyrics = self.extract_lyrics_from_description(description)
            
            if lyrics:
                return lyrics
            
            return "No lyrics found in transcript or description."
            
        except Exception as e:
            return f"Failed to extract lyrics: {e}"
    
    def get_metadata(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata for a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video metadata
        """
        self._ensure_initialized()
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'video_id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'channel': info.get('uploader', ''),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'video_url': url,
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'language': info.get('language', ''),
                    'age_limit': info.get('age_limit', 0)
                }
                
        except Exception as e:
            raise RuntimeError(f"Failed to get metadata: {e}")
    
    def get_anti_detection_status(self) -> Dict[str, Any]:
        """Get anti-detection status for yt-dlp."""
        return self.anti_detection.get_status() if self.anti_detection else {'status': 'disabled'}
    
    def extract_lyrics_from_description(self, description: str) -> Optional[str]:
        """
        Extract lyrics from video description text.
        
        Args:
            description: Video description text
            
        Returns:
            Extracted lyrics if found, None otherwise
        """
        if not description:
            return None
        
        try:
            lines = description.split('\n')
            lyrics = []
            
            for line in lines:
                # Filter out non-lyric lines
                if (not line.startswith("#") and 
                    "http" not in line and 
                    "｜" not in line and 
                    "：" not in line and 
                    "《" not in line and
                    "【" not in line and
                    "】" not in line and
                    len(line.strip()) > 0):
                    lyrics.append(line.strip())
            
            if lyrics:
                return '\n'.join(lyrics)
            return None
            
        except Exception:
            return None
    
    def download_captions(self, url: str, language_code: str = 'en',
                          output_path: str = None) -> str:
        """
        Download captions/subtitles using yt-dlp.

        Args:
            url: YouTube video URL
            language_code: Language code (e.g., 'en', 'es', 'fr')
            output_path: Output directory path or full file path

        Returns:
            Path to downloaded caption file
        """
        self._ensure_initialized()

        try:
            # Extract video ID if full URL provided
            if 'youtube.com' in url or 'youtu.be' in url:
                video_id = self.extract_video_id(url)
            else:
                video_id = url

            # Determine output directory and file pattern
            if output_path:
                if os.path.isdir(output_path):
                    # If output_path is a directory, create file path within it
                    output_dir = output_path
                    output_filename = f"{video_id}.{language_code}"  # yt-dlp will add .srt
                    final_output_path = os.path.join(output_dir, f"{video_id}.{language_code}.srt")
                else:
                    # If output_path is a file path, use its directory and name
                    output_dir = os.path.dirname(output_path)
                    output_filename = os.path.splitext(os.path.basename(output_path))[0]
                    final_output_path = output_path

                # Ensure output directory exists
                ensure_directory(output_dir)
            else:
                # Default to current directory
                output_dir = os.getcwd()
                output_filename = f"{video_id}.{language_code}"
                final_output_path = f"{video_id}.{language_code}.srt"

            # yt-dlp options for subtitle download
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language_code],
                'subtitlesformat': 'srt',
                'outtmpl': os.path.join(output_dir, output_filename),
                'skip_download': True  # Don't download video, just subtitles
            }

            # Add cookie support if YOUTUBE_COOKIES_FILE environment variable is set
            cookies_file = os.getenv('YOUTUBE_COOKIES_FILE')
            if cookies_file and os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file

            # Download subtitles
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded subtitle file in the target directory
            expected_patterns = [
                f"{output_filename}.{language_code}.srt",
                f"{output_filename}.srt",
                f"{video_id}.{language_code}.srt",
                f"{video_id}.srt"
            ]

            subtitle_file_path = None
            for pattern in expected_patterns:
                test_path = os.path.join(output_dir, pattern)
                if os.path.exists(test_path):
                    subtitle_file_path = test_path
                    break

            # Also check current directory in case yt-dlp placed files there
            if not subtitle_file_path:
                for file in os.listdir('.'):
                    if file.endswith('.srt') and (video_id in file or language_code in file):
                        # Move the file to the correct location
                        src_path = os.path.join('.', file)
                        dst_path = os.path.join(output_dir, file)
                        os.rename(src_path, dst_path)
                        subtitle_file_path = dst_path
                        break

            if subtitle_file_path:
                # If the found file is not in the expected final location, move it
                if subtitle_file_path != final_output_path:
                    try:
                        os.rename(subtitle_file_path, final_output_path)
                        subtitle_file_path = final_output_path
                    except Exception:
                        # If rename fails, keep the original path
                        pass

                return subtitle_file_path
            else:
                raise RuntimeError("No subtitle files found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download captions with yt-dlp: {e}")
    
    def get_playlist_urls(self, playlist_url: str) -> List[str]:
        """
        Extract video URLs from playlist using YT-DLP.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of video URLs
        """
        self._ensure_initialized()
        
        try:
            ydl_opts = {
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True
            }
            
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' in info and info['entries']:
                    urls = []
                    for entry in info['entries']:
                        if entry and 'id' in entry:
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                            urls.append(video_url)
                    
                    if urls:
                        print(f"✅ YT-DLP playlist: {len(urls)} videos found")
                        return urls
                    else:
                        print("⚠️  YT-DLP playlist: No videos found")
                        return []
                else:
                    print("⚠️  YT-DLP playlist: No entries found")
                    return []
                    
        except Exception as e:
            print(f"❌ YT-DLP playlist failed: {e}")
            return []

    # ==================== NEW FEATURES v0.5 ====================

    def extract_cookies_from_browser(self, browser: str = 'chrome') -> str:
        """
        Extract cookies from browser and return path to cookies file.

        yt-dlp supports extracting cookies from: chrome, firefox, safari, edge,
        opera, brave, chromium, vivaldi.

        Args:
            browser: Browser name ('chrome', 'firefox', 'safari', 'edge', 'opera',
                     'brave', 'chromium', 'vivaldi')

        Returns:
            Path to temporary cookies file, or browser name for direct use
        """
        supported_browsers = [
            'chrome', 'firefox', 'safari', 'edge', 'opera',
            'brave', 'chromium', 'vivaldi'
        ]

        browser = browser.lower()
        if browser not in supported_browsers:
            raise ValueError(f"Unsupported browser: {browser}. Supported: {supported_browsers}")

        return browser  # yt-dlp accepts browser name directly with --cookies-from-browser

    def get_video_info_with_cookies_from_browser(self, url: str, browser: str = 'chrome') -> Dict[str, Any]:
        """
        Get video info using cookies extracted from browser.
        Useful for age-restricted or member-only content.

        Args:
            url: YouTube video URL
            browser: Browser to extract cookies from

        Returns:
            Dictionary with video details
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'cookiesfrombrowser': (browser,)
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_video_info(info, url)

        except Exception as e:
            raise RuntimeError(f"Failed to get video info with browser cookies: {e}")

    def _format_video_info(self, info: Dict, url: str) -> Dict[str, Any]:
        """Format raw yt-dlp info dict into standardized format."""
        return {
            'video_id': info.get('id', ''),
            'title': info.get('title', ''),
            'description': info.get('description', ''),
            'duration': info.get('duration', 0),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'comment_count': info.get('comment_count', 0),
            'upload_date': info.get('upload_date', ''),
            'channel': info.get('uploader', ''),
            'channel_id': info.get('channel_id', ''),
            'channel_url': info.get('channel_url', ''),
            'thumbnail_url': info.get('thumbnail', ''),
            'video_url': url,
            'tags': info.get('tags', []),
            'categories': info.get('categories', []),
            'language': info.get('language', ''),
            'age_limit': info.get('age_limit', 0),
            'is_live': info.get('is_live', False),
            'was_live': info.get('was_live', False),
            'availability': info.get('availability', ''),
        }

    def get_heatmap(self, url: str) -> List[Dict[str, Any]]:
        """
        Get viewer engagement heatmap data (most replayed sections).

        Args:
            url: YouTube video URL

        Returns:
            List of heatmap segments with start_time, end_time, and value (intensity)
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                heatmap = info.get('heatmap', [])
                if heatmap:
                    return [
                        {
                            'start_time': segment.get('start_time', 0),
                            'end_time': segment.get('end_time', 0),
                            'value': segment.get('value', 0),
                        }
                        for segment in heatmap
                    ]

                return []

        except Exception as e:
            raise RuntimeError(f"Failed to get heatmap data: {e}")

    def get_chapters(self, url: str) -> List[Dict[str, Any]]:
        """
        Get video chapters using yt-dlp.

        Args:
            url: YouTube video URL

        Returns:
            List of chapters with title, start_time, end_time
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                chapters = info.get('chapters', [])
                if chapters:
                    result = []
                    for chapter in chapters:
                        start = chapter.get('start_time', 0)
                        end = chapter.get('end_time', 0)
                        result.append({
                            'title': chapter.get('title', ''),
                            'start_time': start,
                            'end_time': end,
                            'duration': end - start,
                            'formatted_start': self._format_time(start),
                            'formatted_end': self._format_time(end),
                        })
                    return result

                return []

        except Exception as e:
            raise RuntimeError(f"Failed to get chapters: {e}")

    def _format_time(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS or MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def download_thumbnail(self, url: str, output_path: str = None,
                           quality: str = 'best') -> str:
        """
        Download video thumbnail.

        Args:
            url: YouTube video URL
            output_path: Output directory or file path
            quality: Thumbnail quality ('best', 'default', 'medium', 'high', 'standard', 'maxres')

        Returns:
            Path to downloaded thumbnail file
        """
        self._ensure_initialized()

        try:
            video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

            if output_path is None:
                output_path = os.path.join(os.getcwd(), 'temp')

            ensure_directory(output_path)

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writethumbnail': True,
                'skip_download': True,
                'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            }

            # Add thumbnail conversion if needed
            if quality != 'best':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                }]

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find the downloaded thumbnail
            for ext in ['webp', 'jpg', 'jpeg', 'png']:
                thumb_path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(thumb_path):
                    return thumb_path

            raise RuntimeError("Thumbnail file not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download thumbnail: {e}")

    def get_comments(self, url: str, max_comments: int = 100,
                     sort: str = 'top') -> List[Dict[str, Any]]:
        """
        Extract comments from a YouTube video.

        Args:
            url: YouTube video URL
            max_comments: Maximum number of comments to retrieve
            sort: Sort order ('top' or 'new')

        Returns:
            List of comment dictionaries with author, text, likes, replies, etc.
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'getcomments': True,
                'extractor_args': {
                    'youtube': {
                        'comment_sort': [sort],
                        'max_comments': [str(max_comments), 'all', '100']  # max, max_parents, max_replies
                    }
                }
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                comments = info.get('comments', [])
                if comments:
                    result = []
                    for comment in comments[:max_comments]:
                        result.append({
                            'id': comment.get('id', ''),
                            'text': comment.get('text', ''),
                            'author': comment.get('author', ''),
                            'author_id': comment.get('author_id', ''),
                            'author_thumbnail': comment.get('author_thumbnail', ''),
                            'author_is_uploader': comment.get('author_is_uploader', False),
                            'author_is_verified': comment.get('author_is_verified', False),
                            'like_count': comment.get('like_count', 0),
                            'is_favorited': comment.get('is_favorited', False),
                            'is_pinned': comment.get('is_pinned', False),
                            'timestamp': comment.get('timestamp', 0),
                            'time_text': comment.get('time_text', ''),
                            'parent': comment.get('parent', 'root'),
                        })
                    return result

                return []

        except Exception as e:
            raise RuntimeError(f"Failed to extract comments: {e}")

    def get_sponsorblock_segments(self, url: str) -> List[Dict[str, Any]]:
        """
        Get SponsorBlock segments for a video.

        SponsorBlock is a crowdsourced database of sponsored segments, intros,
        outros, and other skippable content.

        Args:
            url: YouTube video URL

        Returns:
            List of segment dictionaries with category, start, end times
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web']
                    }
                }
            }

            # First get video info to get the video ID
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id', '')

            # Query SponsorBlock API directly
            import urllib.request
            import json

            sb_url = f"https://sponsor.ajay.app/api/skipSegments?videoID={video_id}"

            try:
                with urllib.request.urlopen(sb_url, timeout=10) as response:
                    segments = json.loads(response.read().decode())

                    return [
                        {
                            'category': seg.get('category', ''),
                            'action_type': seg.get('actionType', 'skip'),
                            'start_time': seg.get('segment', [0, 0])[0],
                            'end_time': seg.get('segment', [0, 0])[1],
                            'duration': seg.get('segment', [0, 0])[1] - seg.get('segment', [0, 0])[0],
                            'uuid': seg.get('UUID', ''),
                            'votes': seg.get('votes', 0),
                            'description': self._get_sponsorblock_category_description(seg.get('category', '')),
                        }
                        for seg in segments
                    ]
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return []  # No segments found for this video
                raise

        except Exception as e:
            # SponsorBlock is optional, don't fail hard
            return []

    def _get_sponsorblock_category_description(self, category: str) -> str:
        """Get human-readable description for SponsorBlock category."""
        descriptions = {
            'sponsor': 'Sponsored segment',
            'selfpromo': 'Self-promotion / Unpaid promotion',
            'interaction': 'Interaction reminder (subscribe, like)',
            'intro': 'Intro animation / Intro sequence',
            'outro': 'Outro / End cards',
            'preview': 'Preview / Recap',
            'music_offtopic': 'Non-music section in music video',
            'filler': 'Filler / Tangent',
            'exclusive_access': 'Exclusive access / Premium content',
            'poi_highlight': 'Point of interest / Highlight',
        }
        return descriptions.get(category, category)

    def download_with_sponsorblock(self, url: str, output_path: str = None,
                                   action: str = 'remove',
                                   categories: List[str] = None) -> str:
        """
        Download video with SponsorBlock segments handled.

        Args:
            url: YouTube video URL
            output_path: Output directory
            action: What to do with segments ('remove', 'mark' as chapters, 'skip')
            categories: Categories to handle. Default: ['sponsor', 'selfpromo', 'intro', 'outro']

        Returns:
            Path to downloaded file
        """
        self._ensure_initialized()

        if categories is None:
            categories = ['sponsor', 'selfpromo', 'intro', 'outro']

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
        }

        # Add SponsorBlock postprocessor
        if action == 'remove':
            ydl_opts['postprocessors'] = [{
                'key': 'SponsorBlock',
                'categories': categories,
                'when': 'pre_process',
            }, {
                'key': 'ModifyChapters',
                'remove_sponsor_segments': categories,
            }]
        elif action == 'mark':
            ydl_opts['postprocessors'] = [{
                'key': 'SponsorBlock',
                'categories': categories,
            }, {
                'key': 'ModifyChapters',
                'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
            }]

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv']:
                video_path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(video_path):
                    return video_path

            raise RuntimeError("Video file not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download with SponsorBlock: {e}")

    def convert_subtitles(self, input_path: str, output_format: str = 'srt') -> str:
        """
        Convert subtitle file to different format.

        Args:
            input_path: Path to input subtitle file
            output_format: Output format ('srt', 'vtt', 'ass', 'json3', 'ttml')

        Returns:
            Path to converted subtitle file
        """
        self._ensure_initialized()

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Subtitle file not found: {input_path}")

        supported_formats = ['srt', 'vtt', 'ass', 'json3', 'ttml']
        if output_format not in supported_formats:
            raise ValueError(f"Unsupported format: {output_format}. Supported: {supported_formats}")

        # Determine output path
        base_path = os.path.splitext(input_path)[0]
        output_path = f"{base_path}.{output_format}"

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                # Use yt-dlp's subtitle converter
                from yt_dlp.postprocessor import FFmpegSubtitlesConvertorPP

                pp = FFmpegSubtitlesConvertorPP(ydl, format=output_format)

                # Create a minimal info dict for the postprocessor
                info = {
                    'filepath': input_path,
                    'requested_subtitles': {
                        'en': {'filepath': input_path, 'ext': os.path.splitext(input_path)[1][1:]}
                    }
                }

                pp.run(info)

                if os.path.exists(output_path):
                    return output_path

                raise RuntimeError("Converted file not found")

        except Exception as e:
            raise RuntimeError(f"Failed to convert subtitles: {e}")

    def download_live_stream(self, url: str, output_path: str = None,
                             from_start: bool = False,
                             duration: int = None) -> str:
        """
        Download a live stream or live stream archive.

        Args:
            url: YouTube live stream URL
            output_path: Output directory
            from_start: If True, download from the beginning of the stream
            duration: Maximum duration to download in seconds (None for full stream)

        Returns:
            Path to downloaded file
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'live_from_start': from_start,
        }

        # Add duration limit if specified
        if duration:
            ydl_opts['download_ranges'] = lambda info, ydl: [{'start_time': 0, 'end_time': duration}]

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv', 'ts']:
                video_path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(video_path):
                    return video_path

            # Check for partial downloads
            for file in os.listdir(output_path):
                if file.startswith(video_id):
                    return os.path.join(output_path, file)

            raise RuntimeError("Live stream file not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download live stream: {e}")

    def download_with_archive(self, url: str, output_path: str = None,
                              archive_file: str = None,
                              format: str = 'best') -> Optional[str]:
        """
        Download video with archive tracking to prevent re-downloads.

        Args:
            url: YouTube video URL
            output_path: Output directory
            archive_file: Path to archive file (default: 'downloaded.txt' in output_path)
            format: Format specification

        Returns:
            Path to downloaded file, or None if already in archive
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        if archive_file is None:
            archive_file = os.path.join(output_path, 'downloaded.txt')

        # Check if already downloaded
        if os.path.exists(archive_file):
            with open(archive_file, 'r') as f:
                if f"youtube {video_id}" in f.read():
                    return None  # Already downloaded

        ydl_opts = {
            'format': format,
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'download_archive': archive_file,
        }

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv', 'mp3', 'wav', 'm4a']:
                file_path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(file_path):
                    return file_path

            raise RuntimeError("File not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download with archive: {e}")

    def is_in_archive(self, url: str, archive_file: str) -> bool:
        """
        Check if a video is already in the download archive.

        Args:
            url: YouTube video URL
            archive_file: Path to archive file

        Returns:
            True if video is in archive, False otherwise
        """
        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if not os.path.exists(archive_file):
            return False

        with open(archive_file, 'r') as f:
            return f"youtube {video_id}" in f.read()

    def get_live_status(self, url: str) -> Dict[str, Any]:
        """
        Get live stream status information.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with live status info
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'is_live': info.get('is_live', False),
                    'was_live': info.get('was_live', False),
                    'live_status': info.get('live_status', 'not_live'),
                    'release_timestamp': info.get('release_timestamp'),
                    'release_date': info.get('release_date'),
                    'availability': info.get('availability', ''),
                }

        except Exception as e:
            raise RuntimeError(f"Failed to get live status: {e}")

    def download_audio_with_metadata(self, url: str, output_path: str = None,
                                     format: str = 'mp3',
                                     embed_thumbnail: bool = True,
                                     add_metadata: bool = True) -> str:
        """
        Download audio with embedded metadata and thumbnail.

        Args:
            url: YouTube video URL
            output_path: Output directory
            format: Audio format ('mp3', 'm4a', 'opus', 'flac')
            embed_thumbnail: Whether to embed thumbnail in audio file
            add_metadata: Whether to add metadata tags

        Returns:
            Path to downloaded audio file
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        postprocessors = [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
            }
        ]

        if add_metadata:
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            })

        if embed_thumbnail:
            postprocessors.append({
                'key': 'EmbedThumbnail',
            })

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'writethumbnail': embed_thumbnail,
            'postprocessors': postprocessors,
        }

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            audio_path = os.path.join(output_path, f'{video_id}.{format}')
            if os.path.exists(audio_path):
                return audio_path

            # Try other extensions
            for ext in ['mp3', 'm4a', 'opus', 'flac', 'wav']:
                path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(path):
                    return path

            raise RuntimeError("Audio file not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download audio with metadata: {e}")

    def split_by_chapters(self, url: str, output_path: str = None,
                          format: str = 'mp4') -> List[str]:
        """
        Download and split video by chapters.

        Args:
            url: YouTube video URL
            output_path: Output directory
            format: Output format ('mp4', 'mp3', etc.)

        Returns:
            List of paths to split files
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else url

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': f'best[ext={format}]/best' if format in ['mp4', 'webm'] else 'bestaudio/best',
            'outtmpl': os.path.join(output_path, f'{video_id}/%(title)s - %(section_title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegSplitChapters',
            }],
        }

        # Add audio extraction if audio format requested
        if format in ['mp3', 'm4a', 'opus', 'flac']:
            ydl_opts['postprocessors'].insert(0, {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
            })

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find all split files
            chapter_dir = os.path.join(output_path, video_id)
            if os.path.exists(chapter_dir):
                return [
                    os.path.join(chapter_dir, f)
                    for f in os.listdir(chapter_dir)
                    if os.path.isfile(os.path.join(chapter_dir, f))
                ]

            return []

        except Exception as e:
            raise RuntimeError(f"Failed to split by chapters: {e}")

    # ==================== NEW FEATURES v0.6 ====================

    # --- Match Filters ---

    def download_with_filter(self, url: str, output_path: str = None,
                             match_filter: str = None,
                             format: str = 'best') -> Optional[str]:
        """
        Download video only if it matches the filter criteria.

        Filter expressions support:
        - Comparison operators: <, <=, >, >=, =, !=
        - Logical operators: & (and), | (or)
        - Fields: duration, view_count, like_count, upload_date, uploader, title, etc.

        Examples:
            - "duration > 600" - Videos longer than 10 minutes
            - "view_count > 10000" - Videos with more than 10k views
            - "duration > 300 & view_count > 1000" - Combined filter
            - "uploader = 'ChannelName'" - Specific channel
            - "upload_date >= 20240101" - Videos from 2024 onwards

        Args:
            url: YouTube video URL or playlist URL
            output_path: Output directory
            match_filter: Filter expression string
            format: Format specification

        Returns:
            Path to downloaded file, or None if filtered out
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else None

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': format,
            'outtmpl': os.path.join(output_path, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
        }

        if match_filter:
            ydl_opts['match_filter'] = self._ydl.utils.match_filter_func(match_filter)

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                result = ydl.download([url])

            # If result is 0, download was successful (or skipped due to filter)
            # Find the downloaded file
            if video_id:
                for ext in ['mp4', 'webm', 'mkv', 'mp3', 'wav', 'm4a']:
                    file_path = os.path.join(output_path, f'{video_id}.{ext}')
                    if os.path.exists(file_path):
                        return file_path

            # For playlists, find any downloaded files
            for file in os.listdir(output_path):
                file_path = os.path.join(output_path, file)
                if os.path.isfile(file_path) and not file.endswith('.part'):
                    return file_path

            return None  # Filtered out or no match

        except Exception as e:
            if 'filter' in str(e).lower() or 'rejected' in str(e).lower():
                return None  # Filtered out
            raise RuntimeError(f"Failed to download with filter: {e}")

    def get_videos_matching_filter(self, url: str, match_filter: str = None,
                                   max_results: int = None) -> List[Dict[str, Any]]:
        """
        Get video info for videos matching the filter criteria (without downloading).

        Useful for previewing what would be downloaded before actually downloading.

        Args:
            url: YouTube video, playlist, or channel URL
            match_filter: Filter expression string
            max_results: Maximum number of results to return

        Returns:
            List of video info dictionaries that match the filter
        """
        self._ensure_initialized()

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'ignoreerrors': True,  # Continue on errors
        }

        if match_filter:
            ydl_opts['match_filter'] = self._ydl.utils.match_filter_func(match_filter)

        if max_results:
            ydl_opts['playlistend'] = max_results

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                results = []

                # Handle playlists
                if 'entries' in info and info['entries']:
                    for entry in info['entries']:
                        if entry:  # Entry might be None if filtered out
                            results.append(self._format_video_info(entry, entry.get('webpage_url', '')))
                else:
                    # Single video
                    results.append(self._format_video_info(info, url))

                return results[:max_results] if max_results else results

        except Exception as e:
            raise RuntimeError(f"Failed to get videos with filter: {e}")

    def filter_playlist(self, playlist_url: str, match_filter: str = None,
                        date_range: tuple = None,
                        min_views: int = None,
                        max_views: int = None,
                        min_duration: int = None,
                        max_duration: int = None,
                        title_contains: str = None,
                        title_not_contains: str = None) -> List[Dict[str, Any]]:
        """
        Filter playlist videos with convenient parameter options.

        This is a higher-level wrapper around match_filter for common use cases.

        Args:
            playlist_url: YouTube playlist URL
            match_filter: Raw filter expression (if provided, other params are ignored)
            date_range: Tuple of (start_date, end_date) in YYYYMMDD format
            min_views: Minimum view count
            max_views: Maximum view count
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            title_contains: Title must contain this string (case-insensitive)
            title_not_contains: Title must NOT contain this string

        Returns:
            List of matching video info dictionaries
        """
        # Build filter expression from parameters if no raw filter provided
        if not match_filter:
            conditions = []

            if date_range:
                start_date, end_date = date_range
                if start_date:
                    conditions.append(f"upload_date >= {start_date}")
                if end_date:
                    conditions.append(f"upload_date <= {end_date}")

            if min_views is not None:
                conditions.append(f"view_count >= {min_views}")
            if max_views is not None:
                conditions.append(f"view_count <= {max_views}")

            if min_duration is not None:
                conditions.append(f"duration >= {min_duration}")
            if max_duration is not None:
                conditions.append(f"duration <= {max_duration}")

            if conditions:
                match_filter = " & ".join(conditions)

        # Get filtered videos
        videos = self.get_videos_matching_filter(playlist_url, match_filter)

        # Apply title filters (not supported by yt-dlp's match_filter)
        if title_contains:
            title_contains = title_contains.lower()
            videos = [v for v in videos if title_contains in v.get('title', '').lower()]

        if title_not_contains:
            title_not_contains = title_not_contains.lower()
            videos = [v for v in videos if title_not_contains not in v.get('title', '').lower()]

        return videos

    def batch_download_with_filter(self, url: str, output_path: str = None,
                                   match_filter: str = None,
                                   format: str = 'best',
                                   max_downloads: int = None,
                                   skip_existing: bool = True) -> List[str]:
        """
        Download multiple videos from playlist/channel with filter.

        Args:
            url: YouTube playlist or channel URL
            output_path: Output directory
            match_filter: Filter expression
            format: Format specification
            max_downloads: Maximum number of videos to download
            skip_existing: Skip videos that already exist in output_path

        Returns:
            List of paths to downloaded files
        """
        self._ensure_initialized()

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': format,
            'outtmpl': os.path.join(output_path, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'ignoreerrors': True,  # Continue on errors
        }

        if match_filter:
            ydl_opts['match_filter'] = self._ydl.utils.match_filter_func(match_filter)

        if max_downloads:
            ydl_opts['playlistend'] = max_downloads

        if skip_existing:
            # Use archive to track downloads
            archive_file = os.path.join(output_path, '.download_archive.txt')
            ydl_opts['download_archive'] = archive_file

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find all downloaded files
            downloaded_files = []
            for file in os.listdir(output_path):
                file_path = os.path.join(output_path, file)
                if os.path.isfile(file_path) and not file.startswith('.') and not file.endswith('.part'):
                    downloaded_files.append(file_path)

            return downloaded_files

        except Exception as e:
            raise RuntimeError(f"Failed batch download with filter: {e}")

    # --- Metadata File Export ---

    def download_with_metadata_files(self, url: str, output_path: str = None,
                                     write_info_json: bool = True,
                                     write_description: bool = True,
                                     write_thumbnail: bool = True,
                                     write_subtitles: bool = False,
                                     subtitle_langs: List[str] = None,
                                     format: str = 'best') -> Dict[str, str]:
        """
        Download video with accompanying metadata files.

        Creates separate files for metadata, description, thumbnail, and subtitles.

        Args:
            url: YouTube video URL
            output_path: Output directory
            write_info_json: Create .info.json file with all metadata
            write_description: Create .description file
            write_thumbnail: Download thumbnail image
            write_subtitles: Download subtitle files
            subtitle_langs: List of subtitle languages (default: ['en'])
            format: Video format specification

        Returns:
            Dictionary mapping file types to their paths
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else None

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        ydl_opts = {
            'format': format,
            'outtmpl': os.path.join(output_path, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
            'writeinfojson': write_info_json,
            'writedescription': write_description,
            'writethumbnail': write_thumbnail,
        }

        if write_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = subtitle_langs or ['en']

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Collect all created files
            result = {}

            if video_id:
                base_path = os.path.join(output_path, video_id)

                # Find main video file
                for ext in ['mp4', 'webm', 'mkv']:
                    video_path = f"{base_path}.{ext}"
                    if os.path.exists(video_path):
                        result['video'] = video_path
                        break

                # Check for metadata files
                if write_info_json:
                    json_path = f"{base_path}.info.json"
                    if os.path.exists(json_path):
                        result['info_json'] = json_path

                if write_description:
                    desc_path = f"{base_path}.description"
                    if os.path.exists(desc_path):
                        result['description'] = desc_path

                if write_thumbnail:
                    for ext in ['webp', 'jpg', 'jpeg', 'png']:
                        thumb_path = f"{base_path}.{ext}"
                        if os.path.exists(thumb_path):
                            result['thumbnail'] = thumb_path
                            break

                if write_subtitles:
                    # Find subtitle files
                    for file in os.listdir(output_path):
                        if file.startswith(video_id) and file.endswith(('.srt', '.vtt', '.ass')):
                            if 'subtitles' not in result:
                                result['subtitles'] = []
                            result['subtitles'].append(os.path.join(output_path, file))

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to download with metadata files: {e}")

    def export_metadata_only(self, url: str, output_path: str = None,
                             format_type: str = 'json') -> str:
        """
        Export video metadata without downloading the video.

        Args:
            url: YouTube video URL
            output_path: Output file path or directory
            format_type: Output format ('json', 'description', 'all')

        Returns:
            Path to the exported metadata file
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else None

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        # Determine if output_path is a directory or file
        if os.path.isdir(output_path) or not os.path.splitext(output_path)[1]:
            ensure_directory(output_path)
            base_path = os.path.join(output_path, video_id or 'video')
        else:
            ensure_directory(os.path.dirname(output_path))
            base_path = os.path.splitext(output_path)[0]

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'outtmpl': f"{base_path}.%(ext)s",
        }

        if format_type in ['json', 'all']:
            ydl_opts['writeinfojson'] = True

        if format_type in ['description', 'all']:
            ydl_opts['writedescription'] = True

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Return the appropriate file path
            if format_type == 'json':
                return f"{base_path}.info.json"
            elif format_type == 'description':
                return f"{base_path}.description"
            else:
                return base_path  # Base path for 'all'

        except Exception as e:
            raise RuntimeError(f"Failed to export metadata: {e}")

    def get_full_metadata(self, url: str) -> Dict[str, Any]:
        """
        Get comprehensive metadata for a video (more fields than get_video_info).

        Includes all available fields from yt-dlp extraction.

        Args:
            url: YouTube video URL

        Returns:
            Dictionary with comprehensive metadata
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Return comprehensive metadata
                return {
                    # Basic info
                    'id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'upload_date': info.get('upload_date', ''),
                    'timestamp': info.get('timestamp'),
                    'duration': info.get('duration', 0),
                    'duration_string': info.get('duration_string', ''),

                    # Channel info
                    'uploader': info.get('uploader', ''),
                    'uploader_id': info.get('uploader_id', ''),
                    'uploader_url': info.get('uploader_url', ''),
                    'channel': info.get('channel', ''),
                    'channel_id': info.get('channel_id', ''),
                    'channel_url': info.get('channel_url', ''),
                    'channel_follower_count': info.get('channel_follower_count'),
                    'channel_is_verified': info.get('channel_is_verified', False),

                    # Engagement metrics
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count'),
                    'dislike_count': info.get('dislike_count'),
                    'comment_count': info.get('comment_count'),
                    'average_rating': info.get('average_rating'),

                    # Thumbnails
                    'thumbnail': info.get('thumbnail', ''),
                    'thumbnails': info.get('thumbnails', []),

                    # Categories and tags
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', []),

                    # Live stream info
                    'is_live': info.get('is_live', False),
                    'was_live': info.get('was_live', False),
                    'live_status': info.get('live_status'),
                    'release_timestamp': info.get('release_timestamp'),
                    'release_date': info.get('release_date'),
                    'release_year': info.get('release_year'),

                    # Availability
                    'availability': info.get('availability', ''),
                    'age_limit': info.get('age_limit', 0),
                    'playable_in_embed': info.get('playable_in_embed', True),

                    # Technical info
                    'webpage_url': info.get('webpage_url', url),
                    'original_url': info.get('original_url', url),
                    'extractor': info.get('extractor', ''),
                    'extractor_key': info.get('extractor_key', ''),

                    # Chapters and heatmap
                    'chapters': info.get('chapters', []),
                    'heatmap': info.get('heatmap', []),

                    # Format info
                    'format': info.get('format', ''),
                    'format_id': info.get('format_id', ''),
                    'format_note': info.get('format_note', ''),
                    'resolution': info.get('resolution', ''),
                    'fps': info.get('fps'),
                    'vcodec': info.get('vcodec', ''),
                    'acodec': info.get('acodec', ''),
                    'abr': info.get('abr'),
                    'vbr': info.get('vbr'),
                    'tbr': info.get('tbr'),
                    'filesize': info.get('filesize'),
                    'filesize_approx': info.get('filesize_approx'),

                    # Subtitles info
                    'subtitles': list(info.get('subtitles', {}).keys()),
                    'automatic_captions': list(info.get('automatic_captions', {}).keys()),

                    # Available formats count
                    'formats_count': len(info.get('formats', [])),
                }

        except Exception as e:
            raise RuntimeError(f"Failed to get full metadata: {e}")

    # --- YouTube Shorts Support ---

    def is_youtube_short(self, url: str) -> bool:
        """
        Check if a URL is a YouTube Short.

        Args:
            url: YouTube URL

        Returns:
            True if the URL is a YouTube Short
        """
        # Check URL patterns for Shorts
        shorts_patterns = [
            r'youtube\.com/shorts/',
            r'youtu\.be/shorts/',
        ]

        for pattern in shorts_patterns:
            if re.search(pattern, url):
                return True

        # Also check video duration if it's a regular URL
        # Shorts are typically under 60 seconds
        if self.is_valid_youtube_url(url) and '/shorts/' not in url:
            try:
                info = self.get_video_info(url)
                duration = info.get('duration', 0)
                # YouTube Shorts are max 60 seconds
                return duration <= 60
            except:
                pass

        return False

    def get_shorts_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a YouTube Short.

        Args:
            url: YouTube Shorts URL

        Returns:
            Dictionary with Shorts-specific info
        """
        self._ensure_initialized()

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'id': info.get('id', ''),
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'is_short': info.get('duration', 0) <= 60,
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'uploader': info.get('uploader', ''),
                    'channel': info.get('channel', ''),
                    'channel_id': info.get('channel_id', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'upload_date': info.get('upload_date', ''),
                    'webpage_url': info.get('webpage_url', url),
                    # Shorts-specific
                    'original_url': url,
                    'is_vertical': True,  # Shorts are always vertical (9:16)
                }

        except Exception as e:
            raise RuntimeError(f"Failed to get Shorts info: {e}")

    def download_short(self, url: str, output_path: str = None,
                       format: str = 'mp4',
                       with_audio: bool = True) -> str:
        """
        Download a YouTube Short.

        Args:
            url: YouTube Shorts URL
            output_path: Output directory
            format: Output format ('mp4', 'webm')
            with_audio: Include audio in download

        Returns:
            Path to downloaded Short file
        """
        self._ensure_initialized()

        video_id = self.extract_video_id(url) if self.is_valid_youtube_url(url) else None

        # Handle Shorts URLs that may have different format
        if '/shorts/' in url and video_id is None:
            # Extract ID from /shorts/VIDEO_ID format
            match = re.search(r'/shorts/([^/?&]+)', url)
            if match:
                video_id = match.group(1)

        if output_path is None:
            output_path = os.path.join(os.getcwd(), 'temp')

        ensure_directory(output_path)

        if with_audio:
            format_spec = f'best[ext={format}]/best'
        else:
            format_spec = f'bestvideo[ext={format}]/bestvideo'

        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
            'quiet': False,
            'no_warnings': True,
        }

        try:
            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Find downloaded file
            for ext in ['mp4', 'webm', 'mkv']:
                file_path = os.path.join(output_path, f'{video_id}.{ext}')
                if os.path.exists(file_path):
                    return file_path

            raise RuntimeError("Short file not found after download")

        except Exception as e:
            raise RuntimeError(f"Failed to download Short: {e}")

    def get_channel_shorts(self, channel_url: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get all Shorts from a YouTube channel.

        Args:
            channel_url: YouTube channel URL
            max_results: Maximum number of Shorts to retrieve

        Returns:
            List of Shorts info dictionaries
        """
        self._ensure_initialized()

        # Convert channel URL to Shorts tab URL
        if '/shorts' not in channel_url:
            if channel_url.endswith('/'):
                shorts_url = channel_url + 'shorts'
            else:
                shorts_url = channel_url + '/shorts'
        else:
            shorts_url = channel_url

        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlistend': max_results,
            }

            with self._ydl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(shorts_url, download=False)

                shorts = []
                if 'entries' in info and info['entries']:
                    for entry in info['entries']:
                        if entry:
                            shorts.append({
                                'id': entry.get('id', ''),
                                'title': entry.get('title', ''),
                                'url': f"https://www.youtube.com/shorts/{entry.get('id', '')}",
                                'duration': entry.get('duration', 0),
                                'view_count': entry.get('view_count'),
                                'uploader': entry.get('uploader', ''),
                            })

                return shorts

        except Exception as e:
            raise RuntimeError(f"Failed to get channel Shorts: {e}")

    def batch_download_shorts(self, channel_url: str, output_path: str = None,
                              max_downloads: int = 10,
                              format: str = 'mp4') -> List[str]:
        """
        Download multiple Shorts from a channel.

        Args:
            channel_url: YouTube channel URL
            output_path: Output directory
            max_downloads: Maximum number of Shorts to download
            format: Output format

        Returns:
            List of paths to downloaded files
        """
        # Get list of Shorts
        shorts = self.get_channel_shorts(channel_url, max_results=max_downloads)

        downloaded = []
        for short in shorts[:max_downloads]:
            try:
                path = self.download_short(
                    short['url'],
                    output_path=output_path,
                    format=format
                )
                downloaded.append(path)
            except Exception as e:
                print(f"Failed to download Short {short['id']}: {e}")
                continue

        return downloaded
