"""
captions.py — captions/subtitles-domain service.

Holds caption listing, download (with handler fallback + format conversion),
search, analytics, export, and the clean-API CaptionResult builder, descended
out of YouTubeToolkit (api.py). api.py keeps one-line delegations; bodies are
verbatim moves with self.* -> self._toolkit.*.

Reads: youtube_toolkit.api.YouTubeToolkit (back-ref), handlers via toolkit,
youtube_toolkit.core.captions.* (filters, result, converter, analyzer).
"""

from typing import Optional, List, Dict, Any
from ..core.fallback import run_with_fallback
from ..core.captions import CaptionResult, CaptionFilters, CaptionTrack


class CaptionsService:
    def __init__(self, toolkit):
        self._toolkit = toolkit

    def get_captions(self, url: str) -> Dict[str, Any]:
        try:
            return self._toolkit.pytubefix.get_captions(url)
        except Exception as e:
            print(f"PyTubeFix captions failed: {e}")
            return {"error": str(e)}

    def download_captions(self, url: str, language_code: str = 'en', output_path: str = None) -> str:
        # Try PyTubeFix first (most reliable), then YT-DLP, then YouTube API.
        return run_with_fallback(
            [
                ("PyTubeFix captions", lambda: self._toolkit.pytubefix.download_captions(url, language_code, output_path)),
                ("YT-DLP captions", lambda: self._toolkit.yt_dlp.download_captions(url, language_code, output_path)),
                ("YouTube API captions", lambda: self._toolkit.youtube_api.download_captions(url, language_code, output_path)),
            ],
            error_message="All caption download methods failed",
            verbose=self._toolkit.verbose,
        )

    def list_captions(self, url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        return self._toolkit.youtube_api.advanced_list_captions(url, filters)

    def advanced_download_captions(self, url: str, language_code: str = 'en',
                                 format: str = 'srt', output_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            # Try YouTube API first (requires OAuth2)
            return self._toolkit.youtube_api.advanced_download_captions(url, language_code=language_code, format=format, output_path=output_path)
        except Exception as api_error:
            # Fall back to yt-dlp handler
            try:
                print(f"YouTube API failed ({api_error}), falling back to yt-dlp...")
                caption_path = self._toolkit.yt_dlp.download_captions(url, language_code, output_path)

                # Read the downloaded caption content
                with open(caption_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()

                # Convert format if needed
                from youtube_toolkit.core.captions import CaptionFormatConverter
                converted_content = raw_content
                if format.lower() == 'vtt':
                    converted_content = CaptionFormatConverter.srt_to_vtt(raw_content)
                elif format.lower() == 'txt':
                    converted_content = CaptionFormatConverter.srt_to_txt(raw_content)

                # Save converted content if different format
                if converted_content != raw_content:
                    output_path = caption_path.replace('.srt', f'.{format}')
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(converted_content)
                    caption_path = output_path

                # Basic analysis
                from youtube_toolkit.core.captions import CaptionFormatConverter, CaptionAnalyzer
                cues = CaptionFormatConverter.parse_srt(raw_content)
                analysis = {
                    'total_duration': sum(cue.duration for cue in cues),
                    'word_count': sum(len(cue.text.split()) for cue in cues),
                    'cue_count': len(cues),
                    'average_cue_duration': sum(cue.duration for cue in cues) / len(cues) if cues else 0,
                    'words_per_minute': CaptionAnalyzer.analyze_reading_speed(cues)['average_wpm'],
                    'language_analysis': CaptionAnalyzer.analyze_language(converted_content),
                    'gaps': CaptionAnalyzer.find_gaps(cues)
                }

                return {
                    'success': True,
                    'output_path': caption_path,
                    'caption_id': 'yt-dlp-fallback',
                    'language_code': language_code,
                    'format': format,
                    'analysis': analysis,
                    'quota_cost': 0
                }
            except Exception as ytdlp_error:
                return {
                    'success': False,
                    'error': f"YouTube API failed: {api_error}. yt-dlp fallback failed: {ytdlp_error}",
                    'quota_cost': 0
                }

    def get_captions_in_format(self, url: str, language_code: str = 'en',
                              format: str = 'vtt') -> str:
        result = self.advanced_download_captions(url, language_code, format)

        if result.get('success'):
            with open(result['output_path'], 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise RuntimeError(f"Failed to get captions: {result.get('error')}")

    def search_captions(self, url: str, search_term: str, language_code: str = 'en') -> List[Dict[str, Any]]:
        from ..core.captions import CaptionFormatConverter

        # Download captions
        result = self.advanced_download_captions(url, language_code, 'srt')

        if not result.get('success'):
            raise RuntimeError(f"Failed to download captions: {result.get('error')}")

        # Parse captions
        if 'content' in result:
            raw_content = result['content'].raw_content
        else:
            # Fallback case - read from file
            with open(result['output_path'], 'r', encoding='utf-8') as f:
                raw_content = f.read()

        from youtube_toolkit.core.captions import CaptionFormatConverter
        cues = CaptionFormatConverter.parse_srt(raw_content)

        # Search for term
        matching_cues = []
        search_lower = search_term.lower()

        for cue in cues:
            if search_lower in cue.text.lower():
                matching_cues.append({
                    'start_time': cue.start_time,
                    'end_time': cue.end_time,
                    'text': cue.text,
                    'formatted_start': cue.formatted_start,
                    'formatted_end': cue.formatted_end
                })

        return matching_cues

    def get_caption_analytics(self, url: str, language_code: str = 'en') -> Dict[str, Any]:
        result = self.advanced_download_captions(url, language_code, 'srt')

        if not result.get('success'):
            raise RuntimeError(f"Failed to download captions: {result.get('error')}")

        return result['analysis']

    def export_captions(self, url: str, format: str = 'json',
                       output_path: Optional[str] = None, language_code: str = 'en') -> str:
        import json
        import csv
        import os
        from datetime import datetime

        # Get caption data
        result = self.advanced_download_captions(url, language_code, 'srt')

        if not result.get('success'):
            raise RuntimeError(f"Failed to download captions: {result.get('error')}")

        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"captions_export_{timestamp}.{format}"
            output_path = os.path.join(os.getcwd(), filename)

        if format.lower() == 'json':
            # Export as JSON with metadata
            export_data = {
                'video_url': url,
                'language_code': language_code,
                'caption_id': result['caption_id'],
                'analysis': result['analysis'],
                'cues': [
                    {
                        'start_time': cue.start_time,
                        'end_time': cue.end_time,
                        'text': cue.text,
                        'formatted_start': cue.formatted_start,
                        'formatted_end': cue.formatted_end
                    } for cue in result['content'].cues
                ]
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

        elif format.lower() == 'csv':
            # Export as CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(['Start Time', 'End Time', 'Duration', 'Text', 'Formatted Start', 'Formatted End'])

                # Write cue data
                for cue in result['content'].cues:
                    writer.writerow([
                        cue.start_time,
                        cue.end_time,
                        cue.duration,
                        cue.text,
                        cue.formatted_start,
                        cue.formatted_end
                    ])

        elif format.lower() in ['srt', 'vtt', 'txt']:
            # Export in caption format
            caption_result = self.advanced_download_captions(url, language_code, format, output_path)
            if not caption_result.get('success'):
                raise RuntimeError(f"Failed to export captions: {caption_result.get('error')}")
            output_path = caption_result['output_path']

        else:
            raise ValueError("Format must be 'json', 'csv', 'srt', 'vtt', or 'txt'")

        return output_path

    def get_best_caption_track(self, url: str, preferred_language: str = 'en') -> Optional[Dict[str, Any]]:
        caption_list = self.list_captions(url)
        tracks = caption_list.get('tracks', [])

        if not tracks:
            return None

        # Find best track using CaptionResult logic
        from ..core.captions import CaptionResult
        result = CaptionResult(tracks=tracks)
        best_track = result.get_best_track(preferred_language)

        if best_track:
            return {
                'caption_id': best_track.caption_id,
                'language': best_track.language,
                'language_code': best_track.language_code,
                'name': best_track.name,
                'track_type': best_track.track_type.value,
                'status': best_track.status.value,
                'is_auto_generated': best_track.is_auto_generated,
                'is_cc': best_track.is_cc,
                'display_name': best_track.display_name
            }

        return None

    def captions(self, url: str, language: str = 'en',
                 filters: Optional[CaptionFilters] = None) -> CaptionResult:
        # Use existing list_captions
        raw_result = self.list_captions(url, filters)

        # Convert to CaptionResult
        tracks = []
        raw_tracks = raw_result.get('tracks', [])

        for raw in raw_tracks:
            if isinstance(raw, CaptionTrack):
                tracks.append(raw)
            # If it's a dict, the list_captions should have already converted it

        return CaptionResult(
            tracks=tracks,
            quota_cost=raw_result.get('quota_cost', 0),
        )
