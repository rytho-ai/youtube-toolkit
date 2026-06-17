"""
Caption data models — enums and dataclasses for the caption domain.

Holds the pure data types for captions: the enums (track type/status/format/
quality) and the dataclasses (track, cue, content, filters, analytics, result,
translation, download options, quality metrics). No conversion or analysis
logic lives here; those are in convert.py and analytics.py respectively.

Reads: dataclasses, typing, datetime, enum (stdlib only — no intra-package deps).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import re

from ..dict_access import DictAccessMixin


class CaptionTrackType(Enum):
    """Caption track types."""
    STANDARD = "standard"
    ASR = "asr"  # Automatic Speech Recognition


class CaptionStatus(Enum):
    """Caption status."""
    SERVING = "serving"
    SYNCING = "syncing"
    FAILED = "failed"


class CaptionFormat(Enum):
    """Caption formats supported by YouTube API."""
    SRT = "srt"  # SubRip subtitle
    VTT = "vtt"  # Web Video Text Tracks caption
    TTML = "ttml"  # Timed Text Markup Language caption
    SBV = "sbv"  # SubViewer subtitle
    SCC = "scc"  # Scenarist Closed Caption format
    TXT = "txt"  # Plain text (converted)


class CaptionQuality(Enum):
    """Caption quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


@dataclass
class CaptionTranslation:
    """Caption translation information."""
    source_language: str
    target_language: str
    is_machine_translated: bool = True
    translation_service: str = "google_translate"
    confidence_score: Optional[float] = None

    @property
    def translation_direction(self) -> str:
        """Get translation direction string."""
        return f"{self.source_language} -> {self.target_language}"


@dataclass
class CaptionDownloadOptions:
    """Advanced caption download options."""
    caption_id: str
    format: CaptionFormat = CaptionFormat.SRT
    target_language: Optional[str] = None  # For translation
    on_behalf_of_content_owner: Optional[str] = None
    validate_format: bool = True
    include_metadata: bool = True

    def validate_options(self) -> List[str]:
        """Validate download options."""
        errors = []

        if not self.caption_id:
            errors.append("Caption ID is required")

        if self.target_language and len(self.target_language) != 2:
            errors.append("Target language must be a 2-letter ISO code")

        return errors


@dataclass
class CaptionQualityMetrics:
    """Caption quality assessment metrics."""
    overall_quality: CaptionQuality = CaptionQuality.UNKNOWN
    timing_accuracy: float = 0.0  # 0-1 score
    text_quality: float = 0.0  # 0-1 score
    completeness: float = 0.0  # 0-1 score
    consistency: float = 0.0  # 0-1 score
    issues: List[str] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        """Get average quality score."""
        scores = [self.timing_accuracy, self.text_quality, self.completeness, self.consistency]
        return sum(scores) / len(scores) if scores else 0.0

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get quality summary."""
        return {
            'overall_quality': self.overall_quality.value,
            'average_score': self.average_score,
            'timing_accuracy': self.timing_accuracy,
            'text_quality': self.text_quality,
            'completeness': self.completeness,
            'consistency': self.consistency,
            'issues_count': len(self.issues),
            'issues': self.issues
        }


@dataclass
class CaptionTrack:
    """Individual caption track information."""
    caption_id: str
    language: str
    language_code: str
    name: str
    track_type: CaptionTrackType
    status: CaptionStatus
    is_auto_generated: bool
    is_cc: bool
    is_draft: bool
    is_easy_reader: bool
    is_large: bool
    last_updated: Optional[datetime] = None

    @property
    def is_manual(self) -> bool:
        """Check if this is a manually created caption track."""
        return not self.is_auto_generated

    @property
    def is_accessible(self) -> bool:
        """Check if this caption track is accessible."""
        return self.status == CaptionStatus.SERVING

    @property
    def display_name(self) -> str:
        """Get display name for the caption track."""
        if self.name:
            return f"{self.name} ({self.language})"
        return self.language


@dataclass
class CaptionCue:
    """Individual caption cue/timestamp."""
    start_time: float  # seconds
    end_time: float    # seconds
    text: str
    speaker: Optional[str] = None

    @property
    def duration(self) -> float:
        """Get cue duration in seconds."""
        return self.end_time - self.start_time

    @property
    def formatted_start(self) -> str:
        """Get formatted start time (HH:MM:SS,mmm)."""
        return self._format_time(self.start_time)

    @property
    def formatted_end(self) -> str:
        """Get formatted end time (HH:MM:SS,mmm)."""
        return self._format_time(self.end_time)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS,mmm format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@dataclass
class CaptionContent:
    """Caption content with cues and metadata."""
    caption_id: str
    language: str
    language_code: str
    cues: List[CaptionCue] = field(default_factory=list)
    format: CaptionFormat = CaptionFormat.SRT
    raw_content: Optional[str] = None

    @property
    def total_duration(self) -> float:
        """Get total caption duration in seconds."""
        if not self.cues:
            return 0.0
        return max(cue.end_time for cue in self.cues)

    @property
    def word_count(self) -> int:
        """Get total word count."""
        return sum(len(cue.text.split()) for cue in self.cues)

    @property
    def cue_count(self) -> int:
        """Get number of cues."""
        return len(self.cues)

    @property
    def average_cue_duration(self) -> float:
        """Get average cue duration."""
        if not self.cues:
            return 0.0
        return sum(cue.duration for cue in self.cues) / len(self.cues)

    def get_cues_in_timeframe(self, start_time: float, end_time: float) -> List[CaptionCue]:
        """Get cues within a specific timeframe."""
        return [
            cue for cue in self.cues
            if cue.start_time >= start_time and cue.end_time <= end_time
        ]

    def search_text(self, search_term: str, case_sensitive: bool = False) -> List[CaptionCue]:
        """Search for text within captions."""
        if not case_sensitive:
            search_term = search_term.lower()

        matching_cues = []
        for cue in self.cues:
            cue_text = cue.text if case_sensitive else cue.text.lower()
            if search_term in cue_text:
                matching_cues.append(cue)

        return matching_cues


@dataclass
class CaptionFilters:
    """Advanced caption filtering options."""
    # Language filtering
    language_codes: Optional[List[str]] = None
    languages: Optional[List[str]] = None

    # Track type filtering
    track_types: Optional[List[CaptionTrackType]] = None
    auto_generated_only: Optional[bool] = None
    manual_only: Optional[bool] = None

    # Status filtering
    statuses: Optional[List[CaptionStatus]] = None
    accessible_only: bool = True

    # Feature filtering
    cc_only: Optional[bool] = None
    draft_only: Optional[bool] = None
    easy_reader_only: Optional[bool] = None
    large_only: Optional[bool] = None

    def validate_filters(self) -> List[str]:
        """Validate filter combinations."""
        errors = []

        if self.auto_generated_only and self.manual_only:
            errors.append("Cannot filter for both auto-generated and manual captions")

        if self.draft_only and self.accessible_only:
            errors.append("Draft captions are not accessible")

        return errors


@dataclass
class CaptionAnalytics:
    """Caption analytics and insights."""
    total_tracks: int = 0
    available_tracks: int = 0
    auto_generated_tracks: int = 0
    manual_tracks: int = 0
    languages: List[str] = field(default_factory=list)
    language_distribution: Dict[str, int] = field(default_factory=dict)
    total_duration: float = 0.0
    total_word_count: int = 0
    average_words_per_minute: float = 0.0
    cue_statistics: Dict[str, float] = field(default_factory=dict)

    def calculate_words_per_minute(self) -> float:
        """Calculate words per minute."""
        if self.total_duration == 0:
            return 0.0
        return (self.total_word_count / self.total_duration) * 60

    def get_language_summary(self) -> Dict[str, Any]:
        """Get language distribution summary."""
        return {
            'total_languages': len(self.languages),
            'languages': self.languages,
            'distribution': self.language_distribution,
            'most_common': max(self.language_distribution.items(), key=lambda x: x[1])[0] if self.language_distribution else None
        }


@dataclass
class CaptionResult(DictAccessMixin):
    """Comprehensive caption result with analytics."""
    tracks: List[CaptionTrack] = field(default_factory=list)
    content: Optional[CaptionContent] = None
    analytics: Optional[CaptionAnalytics] = None
    filters_applied: Optional[CaptionFilters] = None
    quota_cost: int = 50  # Captions API costs 50 units per request

    @property
    def available_tracks(self) -> List[CaptionTrack]:
        """Get only accessible caption tracks."""
        return [track for track in self.tracks if track.is_accessible]

    @property
    def auto_generated_tracks(self) -> List[CaptionTrack]:
        """Get auto-generated caption tracks."""
        return [track for track in self.tracks if track.is_auto_generated]

    @property
    def manual_tracks(self) -> List[CaptionTrack]:
        """Get manually created caption tracks."""
        return [track for track in self.tracks if track.is_manual]

    def get_tracks_by_language(self, language_code: str) -> List[CaptionTrack]:
        """Get tracks by language code."""
        return [track for track in self.tracks if track.language_code == language_code]

    def get_best_track(self, preferred_language: str = 'en') -> Optional[CaptionTrack]:
        """Get the best available track (manual > auto, preferred language)."""
        available = self.available_tracks

        # Try to find manual track in preferred language
        for track in available:
            if track.is_manual and track.language_code == preferred_language:
                return track

        # Try to find any manual track
        for track in available:
            if track.is_manual:
                return track

        # Fall back to auto-generated in preferred language
        for track in available:
            if track.language_code == preferred_language:
                return track

        # Return first available track
        return available[0] if available else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'tracks': [
                {
                    'caption_id': track.caption_id,
                    'language': track.language,
                    'language_code': track.language_code,
                    'name': track.name,
                    'track_type': track.track_type.value,
                    'status': track.status.value,
                    'is_auto_generated': track.is_auto_generated,
                    'is_cc': track.is_cc,
                    'is_draft': track.is_draft,
                    'is_easy_reader': track.is_easy_reader,
                    'is_large': track.is_large,
                    'last_updated': track.last_updated.isoformat() if track.last_updated else None,
                    'display_name': track.display_name
                } for track in self.tracks
            ],
            'content': {
                'caption_id': self.content.caption_id,
                'language': self.content.language,
                'language_code': self.content.language_code,
                'format': self.content.format.value,
                'total_duration': self.content.total_duration,
                'word_count': self.content.word_count,
                'cue_count': self.content.cue_count,
                'average_cue_duration': self.content.average_cue_duration,
                'cues': [
                    {
                        'start_time': cue.start_time,
                        'end_time': cue.end_time,
                        'duration': cue.duration,
                        'text': cue.text,
                        'formatted_start': cue.formatted_start,
                        'formatted_end': cue.formatted_end
                    } for cue in self.content.cues
                ]
            } if self.content else None,
            'analytics': {
                'total_tracks': self.analytics.total_tracks,
                'available_tracks': self.analytics.available_tracks,
                'auto_generated_tracks': self.analytics.auto_generated_tracks,
                'manual_tracks': self.analytics.manual_tracks,
                'languages': self.analytics.languages,
                'language_distribution': self.analytics.language_distribution,
                'total_duration': self.analytics.total_duration,
                'total_word_count': self.analytics.total_word_count,
                'words_per_minute': self.analytics.calculate_words_per_minute()
            } if self.analytics else None,
            'quota_cost': self.quota_cost
        }
