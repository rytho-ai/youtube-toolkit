"""
Caption format conversion — SRT <-> VTT/TXT/SBV/TTML and SRT parsing/validation.

Pure stateless converter: takes raw caption text in one format and emits another,
plus parse_srt() to turn SRT into CaptionCue objects and validate_format() to
sanity-check content. Depends only on the model types in models.py.

Reads: typing; .models (CaptionCue, CaptionFormat).
"""

from typing import List, Dict, Any

from .models import CaptionCue, CaptionFormat


class CaptionFormatConverter:
    """Convert between different caption formats."""

    @staticmethod
    def srt_to_vtt(srt_content: str) -> str:
        """Convert SRT format to WebVTT format."""
        lines = srt_content.strip().split('\n')
        vtt_lines = ['WEBVTT', '']

        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # Cue number
                i += 1
                if i < len(lines):
                    # Time line
                    time_line = lines[i].replace(',', '.')
                    vtt_lines.append(time_line)
                    i += 1
                    # Text lines
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i])
                        i += 1
                    vtt_lines.extend(text_lines)
                    vtt_lines.append('')
            else:
                i += 1

        return '\n'.join(vtt_lines)

    @staticmethod
    def srt_to_txt(srt_content: str) -> str:
        """Convert SRT format to plain text."""
        lines = srt_content.strip().split('\n')
        text_lines = []

        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # Cue number
                i += 2  # Skip number and time
                # Collect text lines
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i])
                    i += 1
            else:
                i += 1

        return '\n'.join(text_lines)

    @staticmethod
    def srt_to_sbv(srt_content: str) -> str:
        """Convert SRT format to SubViewer (SBV) format."""
        lines = srt_content.strip().split('\n')
        sbv_lines = []

        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # Cue number
                i += 1
                if i < len(lines):
                    # Parse time line
                    time_line = lines[i]
                    start_time, end_time = CaptionFormatConverter._parse_srt_time(time_line)
                    sbv_time = f"{CaptionFormatConverter._format_sbv_time(start_time)},{CaptionFormatConverter._format_sbv_time(end_time)}"
                    i += 1

                    # Collect text lines
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i])
                        i += 1

                    if text_lines:
                        sbv_lines.append(sbv_time)
                        sbv_lines.append('\n'.join(text_lines))
                        sbv_lines.append('')

        return '\n'.join(sbv_lines)

    @staticmethod
    def srt_to_ttml(srt_content: str) -> str:
        """Convert SRT format to TTML format."""
        lines = srt_content.strip().split('\n')
        cues = CaptionFormatConverter.parse_srt(srt_content)

        ttml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<tt xmlns="http://www.w3.org/ns/ttml" xmlns:tts="http://www.w3.org/ns/ttml#styling">',
            '  <head>',
            '    <styling>',
            '      <style id="default" tts:fontSize="16px" tts:color="white"/>',
            '    </styling>',
            '  </head>',
            '  <body>',
            '    <div>'
        ]

        for cue in cues:
            start_time = CaptionFormatConverter._format_ttml_time(cue.start_time)
            end_time = CaptionFormatConverter._format_ttml_time(cue.end_time)
            text = cue.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            ttml_lines.append(f'      <p begin="{start_time}" end="{end_time}">{text}</p>')

        ttml_lines.extend([
            '    </div>',
            '  </body>',
            '</tt>'
        ])

        return '\n'.join(ttml_lines)

    @staticmethod
    def _format_sbv_time(seconds: float) -> str:
        """Format time for SBV format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @staticmethod
    def _format_ttml_time(seconds: float) -> str:
        """Format time for TTML format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @staticmethod
    def validate_format(content: str, format_type: CaptionFormat) -> Dict[str, Any]:
        """Validate caption format."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        try:
            if format_type == CaptionFormat.SRT:
                cues = CaptionFormatConverter.parse_srt(content)
                validation_result['stats'] = {
                    'cue_count': len(cues),
                    'total_duration': max(cue.end_time for cue in cues) if cues else 0,
                    'average_cue_duration': sum(cue.duration for cue in cues) / len(cues) if cues else 0
                }

                # Check for common SRT issues
                if not cues:
                    validation_result['errors'].append("No valid cues found")
                    validation_result['is_valid'] = False

                # Check for timing issues
                for i, cue in enumerate(cues):
                    if cue.start_time >= cue.end_time:
                        validation_result['errors'].append(f"Cue {i+1}: Start time >= End time")
                        validation_result['is_valid'] = False

                    if cue.duration > 10:  # Very long cue
                        validation_result['warnings'].append(f"Cue {i+1}: Very long duration ({cue.duration:.1f}s)")

            elif format_type == CaptionFormat.VTT:
                if not content.startswith('WEBVTT'):
                    validation_result['errors'].append("Missing WEBVTT header")
                    validation_result['is_valid'] = False

            elif format_type == CaptionFormat.TTML:
                if '<?xml' not in content or '<tt' not in content:
                    validation_result['errors'].append("Invalid TTML format")
                    validation_result['is_valid'] = False

        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")

        return validation_result

    @staticmethod
    def parse_srt(srt_content: str) -> List[CaptionCue]:
        """Parse SRT content into CaptionCue objects."""
        lines = srt_content.strip().split('\n')
        cues = []

        i = 0
        while i < len(lines):
            if lines[i].strip().isdigit():  # Cue number
                i += 1
                if i < len(lines):
                    # Parse time line
                    time_line = lines[i]
                    start_time, end_time = CaptionFormatConverter._parse_srt_time(time_line)
                    i += 1

                    # Collect text lines
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i])
                        i += 1

                    if text_lines:
                        cue = CaptionCue(
                            start_time=start_time,
                            end_time=end_time,
                            text=' '.join(text_lines)
                        )
                        cues.append(cue)
            else:
                i += 1

        return cues

    @staticmethod
    def _parse_srt_time(time_line: str) -> tuple[float, float]:
        """Parse SRT time format (HH:MM:SS,mmm --> HH:MM:SS,mmm)."""
        # Remove arrow and split
        start_str, end_str = time_line.split(' --> ')

        def parse_time(time_str: str) -> float:
            # Replace comma with dot for milliseconds
            time_str = time_str.replace(',', '.')
            # Parse HH:MM:SS.mmm
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0

            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000

        return parse_time(start_str), parse_time(end_str)
