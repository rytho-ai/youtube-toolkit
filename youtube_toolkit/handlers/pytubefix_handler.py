"""PyTubeFix handler for YouTube Toolkit.

This handler implements video information extraction and media downloading
using the pytubefix package with advanced video processing capabilities.
"""

import os
import re
from typing import Optional, Dict, Any, List
from ..utils.anti_detection import AntiDetectionManager
from ..utils.request_interceptor import anti_detection_interceptor, rate_limit


class PyTubeFixHandler:
    """Handler for PyTubeFix package functionality."""
    
    def __init__(self, anti_detection: AntiDetectionManager = None):
        """Initialize the PyTubeFix handler."""
        self._yt = None
        self._initialized = False
        self.anti_detection = anti_detection or AntiDetectionManager()
    
    def _ensure_initialized(self):
        """Ensure pytubefix is available and initialized."""
        if not self._initialized:
            try:
                from pytubefix import YouTube
                self._YouTube = YouTube
                self._initialized = True
            except ImportError:
                raise ImportError("pytubefix is not installed. Install with: pip install pytubefix")
    
    def _create_yt(self, url, **kwargs):
        """Create a YouTube object with the given URL."""
        self._ensure_initialized()
        return self._YouTube(url, **kwargs)
    
    def sanitize_path(self, name: str) -> str:
        """Remove characters not allowed in file names."""
        return re.sub(r'[\\/:*?"<>|]', '', name)
    
    @anti_detection_interceptor
    @rate_limit(max_requests=5, window_minutes=1)
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information using pytubefix.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video details
        """
        self._ensure_initialized()
        
        try:
            yt = self._create_yt(url)            
            return {
                'video_id': yt.video_id,
                'title': yt.title,
                'description': yt.description,
                'duration': yt.length,
                'view_count': yt.views,
                'like_count': getattr(yt, 'likes', 0),
                'upload_date': str(yt.publish_date) if yt.publish_date else "",
                'channel': yt.author,
                'thumbnail_url': yt.thumbnail_url,
                'video_url': url
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get video info with pytubefix: {e}")
    
    @anti_detection_interceptor
    @rate_limit(max_requests=3, window_minutes=1)
    def download_audio(self, url: str, output_path: str = None,
                       format: str = 'wav', progress_callback: bool = True,
                       bitrate: str = 'best') -> str:
        """
        Downloads the audio from a YouTube video with selectable bitrate and format conversion.

        Args:
            url: YouTube video URL
            output_path: The file path (including filename) where the audio will be saved.
                         Defaults to current directory with the video title as filename.
            format: Audio format ('wav', 'mp3', 'm4a')
            progress_callback: Whether to show download progress
            bitrate: Audio bitrate ('best', '320k', '256k', '192k', '128k', '96k', '64k')

        Returns:
            str: The full path to the downloaded file.
        """
        self._ensure_initialized()

        try:
            from pytubefix.cli import on_progress

            yt = self._create_yt(url, on_progress_callback=on_progress if progress_callback else None)

            # Select audio stream based on bitrate preference
            audio_stream = self._select_audio_stream_by_bitrate(yt, bitrate)

            if not audio_stream:
                raise RuntimeError("No suitable audio streams found.")

            title = self.sanitize_path(yt.title.replace(' ', '-'))

            # Default save path
            if output_path is None:
                output_path = os.path.join(os.getcwd(), f'{title}.{format}')

            out_dir, filename = os.path.split(output_path)
            os.makedirs(out_dir, exist_ok=True)  # Ensure directory exists

            # Download to temporary file first
            temp_filename = f"temp_{filename}"
            temp_path = os.path.join(out_dir, temp_filename)

            audio_stream.download(output_path=out_dir, filename=temp_filename)

            # Convert format and bitrate if needed
            final_path = os.path.join(out_dir, filename)
            self._convert_audio(temp_path, final_path, format, bitrate, progress_callback)

            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return final_path

        except Exception as e:
            raise RuntimeError(f"Failed to download audio: {e}")
    
    def _select_audio_stream_by_bitrate(self, yt, bitrate: str):
        """
        Select the best audio stream based on bitrate preference.
        
        Args:
            yt: PyTubeFix YouTube object
            bitrate: Bitrate preference ('best', '320k', '256k', '192k', '128k', '96k', '64k')
            
        Returns:
            Selected audio stream or None
        """
        audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        
        if not audio_streams:
            return None
        
        if bitrate == 'best':
            return audio_streams.first()  # Highest bitrate
        
        # Extract target bitrate number (e.g., '192k' -> 192)
        try:
            target_bitrate = int(bitrate.replace('k', ''))
        except ValueError:
            return audio_streams.first()  # Invalid format, use best
        
        # Find exact match first
        for stream in audio_streams:
            if stream.abr:
                stream_kbps = int(stream.abr.replace('kbps', ''))
                if stream_kbps == target_bitrate:
                    return stream
        
        # Find closest match (prefer lower bitrate if no exact match)
        best_match = None
        smallest_diff = float('inf')
        
        for stream in audio_streams:
            if stream.abr:
                stream_kbps = int(stream.abr.replace('kbps', ''))
                diff = abs(stream_kbps - target_bitrate)
                # Prefer lower bitrates when difference is equal
                if diff < smallest_diff or (diff == smallest_diff and stream_kbps <= target_bitrate):
                    smallest_diff = diff
                    best_match = stream
        
        return best_match if best_match else audio_streams.first()

    def _convert_audio(self, input_path: str, output_path: str, format: str, bitrate: str, progress_callback: bool = True):
        """
        Convert audio file to specified format and bitrate using FFmpeg.

        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file
            format: Target audio format ('wav', 'mp3', 'm4a')
            bitrate: Target bitrate ('best', '320k', '256k', '192k', '128k', '96k', '64k')
            progress_callback: Whether to show progress messages
        """
        import subprocess

        try:
            # Check if FFmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            if progress_callback:
                print("⚠️  FFmpeg not found. Copying file without conversion...")
            # Fallback: just copy the file
            import shutil
            shutil.copy2(input_path, output_path)
            return

        cmd = ['ffmpeg', '-i', input_path, '-y']  # -y to overwrite output file

        # Add bitrate conversion if not 'best'
        if bitrate != 'best':
            try:
                # Extract numeric bitrate
                bitrate_num = bitrate.replace('k', '')
                cmd.extend(['-b:a', f'{bitrate_num}k'])
            except ValueError:
                if progress_callback:
                    print(f"⚠️  Invalid bitrate '{bitrate}', using original quality")

        # Add format-specific settings
        if format.lower() == 'mp3':
            cmd.extend(['-codec:a', 'libmp3lame'])
        elif format.lower() == 'wav':
            cmd.extend(['-codec:a', 'pcm_s16le'])
        elif format.lower() == 'm4a':
            cmd.extend(['-codec:a', 'aac'])

        # Hide FFmpeg output unless there's an error
        if not progress_callback:
            cmd.extend(['-loglevel', 'error'])

        cmd.append(output_path)

        try:
            if progress_callback:
                print(f"🔄 Converting to {format.upper()} with bitrate {bitrate}...")

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if progress_callback:
                print("✅ Audio conversion completed")

        except subprocess.CalledProcessError as e:
            if progress_callback:
                print(f"⚠️  FFmpeg conversion failed: {e}")
                print(f"FFmpeg stderr: {e.stderr}")
                print("Copying original file...")

            # Fallback: copy original file
            import shutil
            shutil.copy2(input_path, output_path)

    def _select_video_streams(self, yt, quality, progress_callback):
        """Select the best video (and audio) streams for the requested quality.

        Returns a (video_stream, audio_stream) tuple; audio_stream is None when a
        progressive stream (with built-in audio) is chosen.
        """
        video_stream = None
        audio_stream = None

        if quality == 'best':
            # Try to get the highest resolution video stream (without audio)
            video_streams = (
                yt.streams.filter(file_extension="mp4", only_video=True,
                                res=["1080p", "720p", "360p", "240p", "144p"])
                .order_by("resolution")
                .desc()
            )
            video_stream = video_streams.first()

            # If no video-only streams, try progressive streams
            if not video_stream:
                progressive_streams = yt.streams.filter(progressive=True, file_extension="mp4")
                if progressive_streams:
                    video_stream = progressive_streams.order_by("resolution").desc().first()
                    audio_stream = None  # Progressive streams have audio built-in
        else:
            # Try specific resolution first (video-only streams)
            video_streams = yt.streams.filter(file_extension="mp4", only_video=True, res=quality)
            video_stream = video_streams.first()

            # If specific resolution not found, try similar or lower resolutions
            if not video_stream:
                if progress_callback:
                    print(f"Resolution {quality} not available, trying similar resolutions...")

                # Try to find the closest available resolution
                if quality == '720p':
                    # Try 720p, then 1080p, then 480p
                    for res in ['720p', '1080p', '480p']:
                        video_streams = yt.streams.filter(file_extension="mp4", only_video=True, res=res)
                        if video_streams:
                            video_stream = video_streams.first()
                            if progress_callback:
                                print(f"   Using {res} instead of {quality}")
                            break
                elif quality == '1080p':
                    # Try 1080p, then 720p, then 1440p
                    for res in ['1080p', '720p', '1440p']:
                        video_streams = yt.streams.filter(file_extension="mp4", only_video=True, res=res)
                        if video_streams:
                            video_stream = video_streams.first()
                            if progress_callback:
                                print(f"   Using {res} instead of {quality}")
                            break

            # If still no video-only streams, try progressive streams as last resort
            if not video_stream:
                if progress_callback:
                    print(f"No video-only streams found, trying progressive streams...")
                progressive_streams = yt.streams.filter(progressive=True, file_extension="mp4")
                if quality != 'best':
                    progressive_streams = progressive_streams.filter(res=quality)

                if progressive_streams:
                    video_stream = progressive_streams.order_by("resolution").desc().first()
                    audio_stream = None  # Progressive streams have audio built-in
                    if progress_callback:
                        print(f"   Using progressive stream: {video_stream.resolution}")
                else:
                    # Final fallback: best available progressive stream
                    progressive_streams = yt.streams.filter(progressive=True, file_extension="mp4")
                    if progressive_streams:
                        video_stream = progressive_streams.order_by("resolution").desc().first()
                        audio_stream = None
                        if progress_callback:
                            print(f"   Using best progressive stream: {video_stream.resolution}")

        # Get audio stream only if we need separate audio
        if video_stream and (not hasattr(video_stream, 'progressive') or not video_stream.progressive):
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

        return video_stream, audio_stream

    def _resolve_output_paths(self, output_path, title):
        """Resolve the final output directory, filename and combined file path.

        Handles the case where ``output_path`` is a directory, a full file path,
        or ``None`` (defaults to the current directory with the video title).
        """
        # Default save path for final combined file
        if output_path is None:
            output_path = os.path.join(os.getcwd(), f"{title}.mp4")

        # Handle case where output_path is a directory (fix for FFmpeg format error)
        if os.path.isdir(output_path) or output_path.endswith('/') or output_path.endswith('\\'):
            # output_path is a directory, create filename inside it
            out_dir = output_path
            filename = f"{title}.mp4"
            combined_path = os.path.join(out_dir, filename)
        else:
            # output_path includes filename
            out_dir, filename = os.path.split(output_path)
            if not filename:  # Edge case: path ends with separator
                out_dir = output_path
                filename = f"{title}.mp4"
            combined_path = os.path.join(out_dir, filename)

        return out_dir, filename, combined_path

    def _combine_video_audio(self, yt, quality, video_path, audio_path,
                             combined_path, out_dir, filename, progress_callback,
                             VideoFileClip, AudioFileClip):
        """Combine separate video and audio streams into ``combined_path``.

        On MoviePy failure, falls back to downloading a progressive stream
        directly to the final location. Returns True when the fallback path was
        taken (caller should return immediately), False on normal combination.
        """
        # Combine video and audio using MoviePy
        if progress_callback:
            print("Combining video and audio...")

        try:
            # Load clips and create combined video
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)
            video_with_audio = video_clip.with_audio(audio_clip)

            # Use compatible parameters for MoviePy
            try:
                # Try with newer MoviePy version parameters
                if progress_callback:
                    print("Using enhanced encoding settings...")

                # Build parameters dynamically based on MoviePy version
                write_params = {
                    'codec': "libx264",
                    'audio_codec': "aac",
                    'preset': "ultrafast",
                    'threads': 4
                }

                # Add verbose and logger only if supported
                try:
                    # Test if verbose parameter is supported
                    import inspect
                    sig = inspect.signature(video_with_audio.write_videofile)
                    if 'verbose' in sig.parameters:
                        write_params['verbose'] = False
                    if 'logger' in sig.parameters:
                        write_params['logger'] = None
                except:
                    pass

                video_with_audio.write_videofile(combined_path, **write_params)
            except TypeError as e:
                # Fallback for older MoviePy versions
                if progress_callback:
                    print("Falling back to standard encoding settings...")
                try:
                    # Build parameters dynamically based on MoviePy version
                    write_params = {
                        'codec': "libx264",
                        'audio_codec': "aac",
                        'preset': "ultrafast"
                    }

                    # Add verbose and logger only if supported
                    try:
                        import inspect
                        sig = inspect.signature(video_with_audio.write_videofile)
                        if 'verbose' in sig.parameters:
                            write_params['verbose'] = False
                        if 'logger' in sig.parameters:
                            write_params['logger'] = None
                    except:
                        pass

                    video_with_audio.write_videofile(combined_path, **write_params)
                except TypeError:
                    # Final fallback with minimal parameters
                    if progress_callback:
                        print("Using minimal encoding settings...")

                    # Build minimal parameters
                    write_params = {}

                    # Add verbose and logger only if supported
                    try:
                        import inspect
                        sig = inspect.signature(video_with_audio.write_videofile)
                        if 'verbose' in sig.parameters:
                            write_params['verbose'] = False
                        if 'logger' in sig.parameters:
                            write_params['logger'] = None
                    except:
                        pass

                    video_with_audio.write_videofile(combined_path, **write_params)

            if progress_callback:
                print("✅ Video and audio combined successfully!")

            # Clean up clips
            video_clip.close()
            audio_clip.close()
            video_with_audio.close()

        except Exception as e:
            # Clean up partial files if combination fails
            if os.path.exists(combined_path):
                try:
                    os.remove(combined_path)
                except:
                    pass

            # Fallback: download just the video stream without audio
            if progress_callback:
                print(f"⚠️  Audio combination failed: {e}")
                print("📹 Downloading video stream only (without audio)...")

            try:
                # Get progressive stream (video + audio combined)
                progressive_streams = yt.streams.filter(progressive=True, file_extension="mp4")
                if quality == 'best':
                    progressive_streams = progressive_streams.order_by("resolution").desc()
                else:
                    progressive_streams = progressive_streams.filter(res=quality)

                progressive_stream = progressive_streams.first()

                if progressive_stream:
                    if progress_callback:
                        print(f"Downloading progressive stream: {progressive_stream.resolution}")

                    # Download directly to final location
                    progressive_stream.download(output_path=out_dir, filename=filename)

                    if progress_callback:
                        print("✅ Progressive video downloaded successfully!")

                    return True
                else:
                    raise RuntimeError("No suitable progressive streams available for fallback")

            except Exception as fallback_error:
                raise RuntimeError(f"Both advanced processing and fallback failed. Advanced error: {e}. Fallback error: {fallback_error}")

        return False

    @anti_detection_interceptor
    @rate_limit(max_requests=2, window_minutes=1)
    def download_video(self, url: str, output_path: str = None,
                       quality: str = 'best', progress_callback: bool = True) -> str:
        """
        Downloads the video from YouTube with advanced processing.
        Downloads separate video and audio streams, then combines them for best quality.
        
        Args:
            url: YouTube video URL
            output_path: The file path (including filename) where the video will be saved.
                         Defaults to current directory with the video title as filename.
            quality: Video quality ('best', '1080p', '720p', '360p', '240p', '144p')
            progress_callback: Whether to show download progress
            
        Returns:
            str: The full path to the downloaded file
        """
        self._ensure_initialized()
        
        # Check if MoviePy is available
        try:
            from moviepy import VideoFileClip, AudioFileClip
        except ImportError:
            raise ImportError(
                "MoviePy is required for video downloads. "
                "Install it with: pip install moviepy"
            )
        
        try:
            from pytubefix.cli import on_progress
            
            # Configure pytubefix to be less verbose
            yt = self._create_yt(url, on_progress_callback=on_progress if progress_callback else None)
            # Reduce verbose output from pytubefix
            if hasattr(yt, 'bypass_age_gate'):
                yt.bypass_age_gate = True
            
            # Define the output directory for downloads
            output_folder = os.path.join(os.getcwd(), 'temp_downloads')
            os.makedirs(output_folder, exist_ok=True)
            
            # Get video streams based on quality preference with fallback
            video_stream, audio_stream = self._select_video_streams(yt, quality, progress_callback)

            if not video_stream:
                raise RuntimeError("No suitable video streams found.")
            
            if progress_callback:
                print(f"Downloading video in resolution: {video_stream.resolution}")
                if audio_stream:
                    print(f"Downloading audio with bitrate: {audio_stream.abr}")
                    print(f"   Strategy: Separate video + audio streams (best quality)")
                else:
                    print("Using progressive stream (video + audio combined)")
                    print(f"   Strategy: Single stream (faster, but may be lower quality)")
                
                # Show available stream info for debugging
                if progress_callback and hasattr(self, 'verbose') and self.verbose:
                    print(f"   Available video-only streams: {[s.resolution for s in yt.streams.filter(only_video=True)]}")
                    print(f"   Available progressive streams: {[s.resolution for s in yt.streams.filter(progressive=True)]}")
                    print(f"   Available audio streams: {[s.abr for s in yt.streams.filter(only_audio=True)]}")
            
            title = self.sanitize_path(yt.title.replace(' ', '-'))
            
            # Download video and audio separately or use progressive stream
            if audio_stream:
                # Download separate streams
                video_path = video_stream.download(output_path=output_folder, filename="temp_video.mp4")
                audio_path = audio_stream.download(output_path=output_folder, filename="temp_audio.mp4")
            else:
                # Use progressive stream (already has audio)
                video_path = video_stream.download(output_path=output_folder, filename="temp_video.mp4")
                audio_path = None
            
            # Resolve final output directory, filename and combined path
            out_dir, filename, combined_path = self._resolve_output_paths(output_path, title)

            os.makedirs(out_dir, exist_ok=True)
            
            # Process video based on stream type
            if audio_stream:
                # Combine video and audio using MoviePy (with progressive fallback)
                if self._combine_video_audio(
                    yt, quality, video_path, audio_path, combined_path,
                    out_dir, filename, progress_callback,
                    VideoFileClip, AudioFileClip,
                ):
                    # Fallback path downloaded directly to final location
                    return combined_path
            else:
                # Progressive stream already has audio, just copy it
                if progress_callback:
                    print("Progressive stream detected, copying to final location...")
                
                import shutil
                shutil.copy2(video_path, combined_path)
                
                # Clean up temporary files
                if os.path.exists(video_path):
                    os.remove(video_path)
                
                if progress_callback:
                    print("✅ Progressive video copied successfully!")
                
                return combined_path
            
            # Clean up temporary files
            if os.path.exists(video_path):
                os.remove(video_path)
            if audio_stream and os.path.exists(audio_path):
                os.remove(audio_path)
            
            # Clean up temp directory if empty
            try:
                if not os.listdir(output_folder):
                    os.rmdir(output_folder)
            except:
                pass
            
            return combined_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to download video: {e}")
    
    @anti_detection_interceptor
    @rate_limit(max_requests=2, window_minutes=1)
    def download_media(self, url: str, download_type: str = 'audio',
                       output_path: str = None, format: str = 'wav',
                       quality: str = 'best', bitrate: str = 'best',
                       progress_callback: bool = True) -> str:
        """
        Download audio or video from YouTube.

        Args:
            url: YouTube video URL
            download_type: Type of media to download ('audio' or 'video')
            output_path: Output file path (optional)
            format: Audio format for audio downloads
            quality: Video quality for video downloads
            bitrate: Audio bitrate for audio downloads
            progress_callback: Whether to show download progress

        Returns:
            Path to downloaded file
        """
        if download_type.lower() == 'audio':
            return self.download_audio(url, output_path, format, progress_callback, bitrate)
        elif download_type.lower() == 'video':
            return self.download_video(url, output_path, quality, progress_callback)
        else:
            raise ValueError("download_type must be 'audio' or 'video'")
    
    def get_available_formats(self, url: str) -> Dict[str, List]:
        """
        Get available download formats for a video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with available formats
        """
        self._ensure_initialized()
        
        try:
            yt = self._create_yt(url)
            
            # Get video streams
            video_streams = yt.streams.filter(only_video=True)
            audio_streams = yt.streams.filter(only_audio=True)
            
            # Organize by resolution
            video_formats = {}
            for stream in video_streams:
                res = stream.resolution
                if res not in video_formats:
                    video_formats[res] = []
                video_formats[res].append({
                    'itag': stream.itag,
                    'filesize': stream.filesize,
                    'mime_type': stream.mime_type
                })
            
            # Organize audio by bitrate
            audio_formats = {}
            for stream in audio_streams:
                abr = stream.abr
                if abr not in audio_formats:
                    audio_formats[abr] = []
                audio_formats[abr].append({
                    'itag': stream.itag,
                    'filesize': stream.filesize,
                    'mime_type': stream.mime_type
                })
            
            return {
                'video_formats': video_formats,
                'audio_formats': audio_formats,
                'best_video': max(video_formats.keys()) if video_formats else None,
                'best_audio': max(audio_formats.keys()) if audio_formats else None
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to get available formats: {e}")
    
    def test_connection(self, url: str) -> bool:
        """
        Test if pytubefix can connect to a YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._ensure_initialized()
            yt = self._create_yt(url)
            return bool(yt and yt.video_id)
        except Exception:
            return False
    
    def get_anti_detection_status(self) -> Dict[str, Any]:
        """Get anti-detection status for pytubefix."""
        return self.anti_detection.get_status() if self.anti_detection else {'status': 'disabled'}

    def stream_to_buffer(self, url: str, stream_type: str = 'audio',
                         quality: str = 'best') -> bytes:
        """
        Stream video/audio content to a buffer (bytes) without saving to disk.

        Args:
            url: YouTube video URL
            stream_type: 'audio' or 'video'
            quality: For video: 'best', '1080p', '720p', '480p', '360p'
                     For audio: 'best', '128k', '192k', '256k'

        Returns:
            Bytes containing the stream data
        """
        self._ensure_initialized()
        import io

        try:
            yt = self._create_yt(url)

            if stream_type == 'audio':
                stream = yt.streams.get_audio_only()
            else:
                # Video stream
                if quality == 'best':
                    stream = yt.streams.get_highest_resolution()
                else:
                    # Try to get specific resolution
                    resolution = quality if quality.endswith('p') else f"{quality}p"
                    stream = yt.streams.filter(res=resolution, progressive=True).first()
                    if not stream:
                        stream = yt.streams.get_highest_resolution()

            if not stream:
                raise RuntimeError(f"No {stream_type} stream available")

            # Stream to buffer
            buffer = io.BytesIO()
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            return buffer.read()

        except Exception as e:
            raise RuntimeError(f"Failed to stream to buffer: {e}")

    def get_filesize_preview(self, url: str) -> Dict[str, Any]:
        """
        Get filesize preview for available streams without downloading.

        Args:
            url: YouTube video URL

        Returns:
            Dict with filesize info for best audio/video streams
        """
        self._ensure_initialized()

        try:
            yt = self._create_yt(url)
            result = {}

            # Best audio
            audio_stream = yt.streams.get_audio_only()
            if audio_stream:
                filesize = audio_stream.filesize if hasattr(audio_stream, 'filesize') else 0
                result['best_audio'] = {
                    'filesize_bytes': filesize,
                    'filesize_mb': round(filesize / (1024 * 1024), 2) if filesize else 0,
                    'bitrate': getattr(audio_stream, 'abr', 'unknown'),
                    'mime_type': getattr(audio_stream, 'mime_type', 'unknown'),
                }

            # Best video
            video_stream = yt.streams.get_highest_resolution()
            if video_stream:
                filesize = video_stream.filesize if hasattr(video_stream, 'filesize') else 0
                result['best_video'] = {
                    'filesize_bytes': filesize,
                    'filesize_mb': round(filesize / (1024 * 1024), 2) if filesize else 0,
                    'resolution': getattr(video_stream, 'resolution', 'unknown'),
                    'mime_type': getattr(video_stream, 'mime_type', 'unknown'),
                }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to get filesize preview: {e}")

    def get_search_suggestions(self, query: str) -> List[str]:
        """
        Get search autocomplete suggestions for a query.

        Args:
            query: Partial search query

        Returns:
            List of suggested search terms
        """
        self._ensure_initialized()

        try:
            results = self.advanced_search(query, max_results=1)
            return results.get('completion_suggestions', [])
        except Exception:
            return []

    def search_videos(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos using pytubefix search functionality.
        
        Args:
            query: Search query string
            filters: Optional filters for search results (currently not used due to pytubefix limitations)
            max_results: Maximum number of results to return
            
        Returns:
            List of video dictionaries with search results
        """
        self._ensure_initialized()
        
        try:
            from pytubefix.contrib.search import Search
            
            # Note: pytubefix search filters are currently problematic
            # We'll use basic search without filters for now
            print("🔍 Searching with PyTubeFix (basic search)...")
            
            # Create search without filters to avoid the dictionary update error
            search = Search(query)
            results = []
            
            # Convert search results to dictionaries
            for i, video in enumerate(search.videos):
                if i >= max_results:
                    break
                    
                try:
                    results.append({
                        'title': getattr(video, 'title', 'Unknown Title'),
                        'watch_url': getattr(video, 'watch_url', ''),
                        'video_id': getattr(video, 'video_id', ''),
                        'author': getattr(video, 'author', 'Unknown Author'),
                        'length': getattr(video, 'length', 0),
                        'views': getattr(video, 'views', 0),
                        'publish_date': str(getattr(video, 'publish_date', '')) if getattr(video, 'publish_date', None) else None,
                        'description': getattr(video, 'description', '')[:200] + "..." if getattr(video, 'description', '') and len(getattr(video, 'description', '')) > 200 else getattr(video, 'description', '')
                    })
                except Exception as video_error:
                    print(f"Warning: Failed to process video {i}: {video_error}")
                    continue
            
            print(f"✅ PyTubeFix search completed: {len(results)} results found")
            return results
            
        except ImportError:
            print("❌ pytubefix.contrib.search is not available. Update pytubefix to latest version.")
            return []
        except Exception as e:
            print(f"❌ PyTubeFix search failed: {e}")
            return []
    
    def simple_search(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Simple search fallback that doesn't rely on pytubefix.contrib.search.
        This method attempts to search using basic pytubefix functionality.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of video dictionaries with search results
        """
        self._ensure_initialized()
        
        try:
            print("🔍 Trying simple search fallback...")
            
            # Try to use basic pytubefix search if available
            try:
                from pytubefix.contrib.search import Search
                search = Search(query)
                
                results = []
                for i, video in enumerate(search.videos):
                    if i >= max_results:
                        break
                        
                    try:
                        results.append({
                            'title': getattr(video, 'title', 'Unknown Title'),
                            'watch_url': getattr(video, 'watch_url', ''),
                            'video_id': getattr(video, 'video_id', ''),
                            'author': getattr(video, 'author', 'Unknown Author'),
                            'length': getattr(video, 'length', 0),
                            'views': getattr(video, 'views', 0),
                            'publish_date': str(getattr(video, 'publish_date', '')) if getattr(video, 'publish_date', None) else None,
                            'description': getattr(video, 'description', '')[:200] + "..." if getattr(video, 'description', '') and len(getattr(video, 'description', '')) > 200 else getattr(video, 'description', '')
                        })
                    except Exception as video_error:
                        print(f"Warning: Failed to process video {i}: {video_error}")
                        continue
                
                if results:
                    print(f"✅ Simple search completed: {len(results)} results found")
                    return results
                    
            except Exception as simple_error:
                print(f"Simple search failed: {simple_error}")
            
            # If all else fails, return empty results
            print("❌ All search methods failed")
            return []
            
        except Exception as e:
            print(f"❌ Simple search failed: {e}")
            return []
    
    def get_captions(self, url: str) -> Dict[str, Any]:
        """
        Get available captions/subtitles for a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with caption information
        """
        self._ensure_initialized()
        
        try:
            yt = self._create_yt(url)
            captions = yt.captions
            
            if not captions:
                return {"available_captions": [], "note": "No captions available for this video"}
            
            # Get caption details - handle different caption object structures
            caption_info = []
            
            # Try different ways to access captions
            try:
                # Method 1: Direct iteration
                for lang_code, caption in captions.items():
                    caption_info.append({
                        'language_code': lang_code,
                        'language': str(caption),
                        'is_auto_generated': 'a.' in str(lang_code),
                        'caption_id': str(lang_code)
                    })
            except (KeyError, TypeError):
                try:
                    # Method 2: Access by index
                    for i in range(len(captions)):
                        caption = captions[i]
                        lang_code = str(caption)
                        caption_info.append({
                            'language_code': lang_code,
                            'language': str(caption),
                            'is_auto_generated': 'a.' in lang_code,
                            'caption_id': lang_code
                        })
                except Exception:
                    # Method 3: Just get the count and basic info
                    caption_info = [{
                        'language_code': 'unknown',
                        'language': 'Available captions',
                        'is_auto_generated': False,
                        'caption_id': 'unknown'
                    }]
            
            return {
                "available_captions": caption_info,
                "total_captions": len(captions),
                "video_title": yt.title
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to get captions: {e}")
    
    def download_captions(self, url: str, language_code: str = 'en', 
                          output_path: str = None) -> str:
        """
        Download captions/subtitles for a video.
        
        Args:
            url: YouTube video URL
            language_code: Language code (e.g., 'en', 'es', 'fr')
            output_path: Output file path (optional)
            
        Returns:
            Path to downloaded caption file
        """
        self._ensure_initialized()
        
        try:
            yt = self._create_yt(url)
            
            # Get available captions
            captions = yt.captions
            
            if not captions:
                raise RuntimeError("No captions available for this video")
            
            # Find caption in requested language
            caption = None
            
            # Iterate through available captions to find matching language
            for cap in captions:
                if hasattr(cap, 'code') and language_code in str(cap.code):
                    caption = cap
                    break
            
            # Fallback to first available caption
            if not caption:
                caption = list(captions)[0]
                print(f"Language '{language_code}' not available. Using '{caption}' instead.")
            
            # Download caption content - try multiple methods
            caption_text = None
            
            # Method 1: Try the download() method (requires title parameter)
            if hasattr(caption, 'download'):
                try:
                    caption_text = caption.download(title="captions")
                except Exception:
                    pass  # Silently try next method
            
            # Method 2: Try to get the XML content directly
            if not caption_text and hasattr(caption, 'xml_captions'):
                try:
                    caption_text = caption.xml_captions
                except Exception:
                    pass
            
            # Method 3: Try to get the srt content
            if not caption_text and hasattr(caption, 'srt_captions'):
                try:
                    caption_text = caption.srt_captions
                except Exception:
                    pass
            
            # Method 4: Try to get the content attribute
            if not caption_text and hasattr(caption, 'content'):
                try:
                    caption_text = caption.content
                except Exception:
                    pass
            
            # Method 5: Try to get the track attribute
            if not caption_text and hasattr(caption, 'track'):
                try:
                    caption_text = caption.track
                except Exception:
                    pass
            
            # Method 6: Try to get the _caption_track attribute
            if not caption_text and hasattr(caption, '_caption_track'):
                try:
                    caption_text = caption._caption_track
                except Exception:
                    pass
            
            # Method 7: Try to get the url and download manually
            if not caption_text and hasattr(caption, 'url'):
                try:
                    import urllib.request
                    caption_url = caption.url
                    with urllib.request.urlopen(caption_url) as response:
                        caption_text = response.read().decode('utf-8')
                except Exception:
                    pass
            
            # Method 8: Last resort - try to get any text content
            if not caption_text:
                if hasattr(caption, 'code'):
                    caption_text = f"Caption code: {caption.code}"
                elif hasattr(caption, 'lang'):
                    caption_text = f"Caption language: {caption.lang}"
                else:
                    caption_text = f"Caption object: {caption}"
            
            # Determine output path
            if not output_path:
                video_title = self._sanitize_filename(yt.title)
                output_path = f"{video_title}_captions_{language_code}.txt"
            
            # Write caption content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(str(caption_text))
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to download captions: {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Convert filename to safe format for file system."""
        import re
        # Remove/replace invalid characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Limit length
        return safe_name[:100].strip()
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID string
        """
        self._ensure_initialized()
        
        try:
            yt = self._create_yt(url)
            return yt.video_id
        except Exception as e:
            raise RuntimeError(f"Failed to extract video ID: {e}")
    
    def get_playlist_urls(self, playlist_url: str) -> List[str]:
        """
        Extract video URLs from playlist using PyTubeFix.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            List of video URLs
        """
        self._ensure_initialized()

        try:
            from pytubefix import Playlist

            playlist = Playlist(playlist_url)
            urls = list(playlist.video_urls)

            if urls:
                print(f"✅ PyTubeFix playlist: {len(urls)} videos found")
                return urls
            else:
                print("⚠️  PyTubeFix playlist: No videos found")
                return []

        except ImportError:
            print("❌ pytubefix Playlist not available")
            return []
        except Exception as e:
            print(f"❌ PyTubeFix playlist failed: {e}")
            return []

    # =========================================================================
    # Channel Support (NEW)
    # =========================================================================

    @anti_detection_interceptor
    @rate_limit(max_requests=3, window_minutes=1)
    def get_channel_videos(self, channel_url: str,
                           content_type: str = 'videos',
                           limit: Optional[int] = None,
                           sort_by: str = 'newest') -> List[Dict[str, Any]]:
        """
        Get videos from a YouTube channel without API quota.

        Args:
            channel_url: YouTube channel URL (@handle, /channel/ID, or /c/name)
            content_type: 'videos', 'shorts', 'live', or 'playlists'
            limit: Maximum number of items to return (None = all available)
            sort_by: Sort order - 'newest' (default), 'oldest', or 'popular'

        Returns:
            List of video/playlist info dicts

        Example:
            >>> handler.get_channel_videos("https://www.youtube.com/@Fireship")
            >>> handler.get_channel_videos("https://www.youtube.com/@Fireship", content_type='shorts', limit=10)
        """
        self._ensure_initialized()

        try:
            from pytubefix import Channel

            channel = Channel(channel_url)

            # Select content source based on type
            if content_type == 'videos':
                source = channel.videos
            elif content_type == 'shorts':
                source = channel.shorts
            elif content_type == 'live':
                source = channel.live
            elif content_type == 'playlists':
                source = channel.playlists
            else:
                raise ValueError(f"Invalid content_type: {content_type}. Use 'videos', 'shorts', 'live', or 'playlists'")

            results = []
            for i, item in enumerate(source):
                if limit and i >= limit:
                    break

                try:
                    if content_type == 'playlists':
                        # Playlist items have different attributes
                        results.append({
                            'playlist_id': getattr(item, 'playlist_id', ''),
                            'title': getattr(item, 'title', 'Unknown'),
                            'url': getattr(item, 'playlist_url', ''),
                            'video_count': getattr(item, 'length', 0),
                            'owner': getattr(item, 'owner', ''),
                        })
                    else:
                        # Video items (videos, shorts, live)
                        results.append({
                            'video_id': getattr(item, 'video_id', ''),
                            'title': getattr(item, 'title', 'Unknown'),
                            'url': getattr(item, 'watch_url', ''),
                            'author': getattr(item, 'author', ''),
                            'length': getattr(item, 'length', 0),
                            'views': getattr(item, 'views', 0),
                            'publish_date': str(getattr(item, 'publish_date', '')) if getattr(item, 'publish_date', None) else None,
                            'thumbnail_url': getattr(item, 'thumbnail_url', ''),
                        })
                except Exception as item_error:
                    # Skip items that fail to parse
                    continue

            # Sort results if requested
            if sort_by == 'popular' and results:
                results.sort(key=lambda x: x.get('views', 0), reverse=True)
            elif sort_by == 'oldest' and results:
                # Reverse the default newest-first order
                results.reverse()

            return results

        except ImportError:
            raise ImportError("pytubefix Channel not available. Update pytubefix to latest version.")
        except Exception as e:
            raise RuntimeError(f"Failed to get channel {content_type}: {e}")

    def get_channel_info(self, channel_url: str) -> Dict[str, Any]:
        """
        Get channel metadata without API quota.

        Args:
            channel_url: YouTube channel URL (@handle, /channel/ID, or /c/name)

        Returns:
            Dict with channel_name, channel_id, description, thumbnail, views, etc.

        Example:
            >>> handler.get_channel_info("https://www.youtube.com/@Fireship")
        """
        self._ensure_initialized()

        try:
            from pytubefix import Channel

            channel = Channel(channel_url)

            return {
                'channel_name': getattr(channel, 'channel_name', ''),
                'channel_id': getattr(channel, 'channel_id', ''),
                'channel_url': getattr(channel, 'channel_url', ''),
                'vanity_url': getattr(channel, 'vanity_url', ''),
                'description': getattr(channel, 'description', ''),
                'thumbnail_url': getattr(channel, 'thumbnail_url', ''),
                'total_views': getattr(channel, 'views', 0),
                'video_count': getattr(channel, 'length', 0),
                'last_updated': getattr(channel, 'last_updated', None),
            }

        except ImportError:
            raise ImportError("pytubefix Channel not available. Update pytubefix to latest version.")
        except Exception as e:
            raise RuntimeError(f"Failed to get channel info: {e}")

    # =========================================================================
    # Video Chapters & Engagement (NEW)
    # =========================================================================

    def get_video_chapters(self, url: str) -> List[Dict[str, Any]]:
        """
        Get video chapters/timestamps.

        Args:
            url: YouTube video URL

        Returns:
            List of chapter dicts with title, start_seconds, duration

        Example:
            >>> chapters = handler.get_video_chapters("https://www.youtube.com/watch?v=...")
            >>> for ch in chapters:
            ...     print(f"{ch['formatted_start']} - {ch['title']}")
        """
        self._ensure_initialized()

        try:
            yt = self._create_yt(url)
            chapters = getattr(yt, 'chapters', None)

            if not chapters:
                return []

            result = []
            for chapter in chapters:
                start_seconds = getattr(chapter, 'start_seconds', 0)
                duration = getattr(chapter, 'duration', 0)

                # Format start time as HH:MM:SS or MM:SS
                hours, remainder = divmod(start_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours:
                    formatted_start = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    formatted_start = f"{minutes}:{seconds:02d}"

                result.append({
                    'title': getattr(chapter, 'title', ''),
                    'start_seconds': start_seconds,
                    'duration': duration,
                    'end_seconds': start_seconds + duration,
                    'formatted_start': formatted_start,
                })

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to get video chapters: {e}")

    def get_key_moments(self, url: str) -> List[Dict[str, Any]]:
        """
        Get AI-generated key moments/timestamps.

        Args:
            url: YouTube video URL

        Returns:
            List of key moment dicts with title, start_seconds, duration
        """
        self._ensure_initialized()

        try:
            yt = self._create_yt(url)
            key_moments = getattr(yt, 'key_moments', None)

            if not key_moments:
                return []

            return [{
                'title': getattr(km, 'title', ''),
                'start_seconds': getattr(km, 'start_seconds', 0),
                'duration': getattr(km, 'duration', 0),
            } for km in key_moments]

        except Exception as e:
            raise RuntimeError(f"Failed to get key moments: {e}")

    def get_replayed_heatmap(self, url: str) -> List[Dict[str, Any]]:
        """
        Get viewer engagement heatmap data (most replayed segments).

        Args:
            url: YouTube video URL

        Returns:
            List of heatmap segments with start_seconds, duration, intensity (0.0-1.0)
        """
        self._ensure_initialized()

        try:
            yt = self._create_yt(url)
            heatmap = getattr(yt, 'replayed_heatmap', None)

            if not heatmap:
                return []

            # heatmap may be a list of dicts or objects
            if isinstance(heatmap, list):
                return heatmap

            return []

        except Exception as e:
            raise RuntimeError(f"Failed to get replayed heatmap: {e}")

    # =========================================================================
    # Advanced Search with Filters (NEW)
    # =========================================================================

    def _build_search_filter(self, Filter, duration, upload_date, sort_by,
                             features, result_type):
        """Build a pytubefix ``Filter`` object from the requested search options."""
        # Build filter
        filter_obj = Filter.create()

        # Duration filter
        if duration:
            duration_map = {
                'short': Filter.Duration.UNDER_4_MINUTES,
                'medium': Filter.Duration.BETWEEN_4_20_MINUTES,
                'long': Filter.Duration.OVER_20_MINUTES,
            }
            if duration in duration_map:
                filter_obj = filter_obj.duration(duration_map[duration])

        # Upload date filter
        if upload_date:
            date_map = {
                'hour': Filter.UploadDate.LAST_HOUR,
                'today': Filter.UploadDate.TODAY,
                'week': Filter.UploadDate.THIS_WEEK,
                'month': Filter.UploadDate.THIS_MONTH,
                'year': Filter.UploadDate.THIS_YEAR,
            }
            if upload_date in date_map:
                filter_obj = filter_obj.upload_date(date_map[upload_date])

        # Sort by
        if sort_by:
            sort_map = {
                'relevance': Filter.SortBy.RELEVANCE,
                'date': Filter.SortBy.UPLOAD_DATE,
                'views': Filter.SortBy.VIEW_COUNT,
                'rating': Filter.SortBy.RATING,
            }
            if sort_by in sort_map:
                filter_obj = filter_obj.sort_by(sort_map[sort_by])

        # Features
        if features:
            feature_map = {
                'live': Filter.Features.LIVE,
                '4k': Filter.Features._4K,
                'hd': Filter.Features.HD,
                'cc': Filter.Features.SUBTITLES_CC,
                'creative_commons': Filter.Features.CREATIVE_COMMONS,
                '360': Filter.Features._360,
                'vr180': Filter.Features.VR180,
                'hdr': Filter.Features.HDR,
            }
            feature_enums = [feature_map[f] for f in features if f in feature_map]
            if feature_enums:
                filter_obj = filter_obj.feature(feature_enums)

        # Result type
        if result_type:
            type_map = {
                'video': Filter.Type.VIDEO,
                'channel': Filter.Type.CHANNEL,
                'playlist': Filter.Type.PLAYLIST,
            }
            if result_type in type_map:
                filter_obj = filter_obj.type(type_map[result_type])

        return filter_obj

    def _process_search_results(self, search, query, max_results,
                                duration, upload_date, sort_by, features,
                                result_type):
        """Convert pytubefix search results into the advanced_search response dict."""
        # Process results
        videos = []
        for i, v in enumerate(search.videos):
            if i >= max_results:
                break
            videos.append(self._video_to_dict(v))

        shorts = []
        for i, s in enumerate(getattr(search, 'shorts', [])):
            if i >= max_results:
                break
            shorts.append(self._video_to_dict(s))

        channels = []
        for i, c in enumerate(getattr(search, 'channel', [])):
            if i >= max_results:
                break
            channels.append({
                'channel_id': getattr(c, 'channel_id', ''),
                'channel_name': getattr(c, 'channel_name', ''),
            })

        playlists = []
        for i, p in enumerate(getattr(search, 'playlist', [])):
            if i >= max_results:
                break
            playlists.append({
                'playlist_id': getattr(p, 'playlist_id', ''),
                'title': getattr(p, 'title', ''),
            })

        return {
            'videos': videos,
            'shorts': shorts,
            'channels': channels,
            'playlists': playlists,
            'completion_suggestions': getattr(search, 'completion_suggestions', []),
            'query': query,
            'filters_applied': {
                'duration': duration,
                'upload_date': upload_date,
                'sort_by': sort_by,
                'features': features,
                'type': result_type,
            }
        }

    def advanced_search(self, query: str,
                        duration: Optional[str] = None,
                        upload_date: Optional[str] = None,
                        sort_by: Optional[str] = None,
                        features: Optional[List[str]] = None,
                        result_type: str = 'video',
                        max_results: int = 20) -> Dict[str, Any]:
        """
        Search with YouTube-native filters (no API quota).

        Args:
            query: Search query
            duration: 'short' (<4min), 'medium' (4-20min), 'long' (>20min)
            upload_date: 'hour', 'today', 'week', 'month', 'year'
            sort_by: 'relevance', 'date', 'views', 'rating'
            features: List of ['hd', '4k', 'live', 'cc', 'creative_commons', 'hdr', '360', 'vr180']
            result_type: 'video', 'channel', 'playlist'
            max_results: Max results to return

        Returns:
            Dict with videos, shorts, channels, playlists, completion_suggestions

        Example:
            >>> results = handler.advanced_search(
            ...     "python tutorial",
            ...     duration='medium',
            ...     upload_date='month',
            ...     sort_by='views'
            ... )
        """
        self._ensure_initialized()

        try:
            from pytubefix.contrib.search import Search, Filter

            # Build filter from the requested options
            filter_obj = self._build_search_filter(
                Filter, duration, upload_date, sort_by, features, result_type
            )

            # Execute search
            search = Search(query, filters=filter_obj)

            # Process results into the response dict
            return self._process_search_results(
                search, query, max_results,
                duration, upload_date, sort_by, features, result_type
            )

        except ImportError:
            raise ImportError("pytubefix Search with Filter not available. Update pytubefix to latest version.")
        except Exception as e:
            # Fallback to basic search if advanced filters fail
            print(f"⚠️ Advanced search failed ({e}), falling back to basic search...")
            basic_results = self.search_videos(query, max_results=max_results)
            return {
                'videos': basic_results,
                'shorts': [],
                'channels': [],
                'playlists': [],
                'completion_suggestions': [],
                'query': query,
                'filters_applied': None,
                'fallback': True,
            }

    def _video_to_dict(self, video) -> Dict[str, Any]:
        """Convert a pytubefix video object to a dictionary."""
        return {
            'video_id': getattr(video, 'video_id', ''),
            'title': getattr(video, 'title', 'Unknown'),
            'url': getattr(video, 'watch_url', ''),
            'author': getattr(video, 'author', ''),
            'length': getattr(video, 'length', 0),
            'views': getattr(video, 'views', 0),
            'publish_date': str(getattr(video, 'publish_date', '')) if getattr(video, 'publish_date', None) else None,
            'thumbnail_url': getattr(video, 'thumbnail_url', ''),
            'description': (getattr(video, 'description', '') or '')[:200],
        }

    # =========================================================================
    # Rich Playlist Details (NEW)
    # =========================================================================

    def get_playlist_info(self, playlist_url: str) -> Dict[str, Any]:
        """
        Get comprehensive playlist information.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            Dict with title, description, owner, views, length, last_updated, etc.

        Example:
            >>> info = handler.get_playlist_info("https://www.youtube.com/playlist?list=...")
        """
        self._ensure_initialized()

        try:
            from pytubefix import Playlist

            playlist = Playlist(playlist_url)

            return {
                'playlist_id': getattr(playlist, 'playlist_id', ''),
                'title': getattr(playlist, 'title', ''),
                'description': getattr(playlist, 'description', ''),
                'owner': getattr(playlist, 'owner', ''),
                'owner_id': getattr(playlist, 'owner_id', ''),
                'owner_url': getattr(playlist, 'owner_url', ''),
                'video_count': getattr(playlist, 'length', 0),
                'views': getattr(playlist, 'views', 0),
                'last_updated': str(getattr(playlist, 'last_updated', '')) if getattr(playlist, 'last_updated', None) else None,
                'thumbnail_url': getattr(playlist, 'thumbnail_url', ''),
            }

        except ImportError:
            raise ImportError("pytubefix Playlist not available. Update pytubefix to latest version.")
        except Exception as e:
            raise RuntimeError(f"Failed to get playlist info: {e}")
