"""
Caption domain package — models, format conversion, and analytics.

Barrel that preserves the historical `youtube_toolkit.core.captions` import path:
the module was split into models.py (enums + dataclasses), convert.py
(CaptionFormatConverter), and analytics.py (CaptionAnalyzer,
CaptionQualityAssessor), and every original top-level name is re-exported here so
external imports stay byte-for-byte identical.

Reads: .models, .convert, .analytics.
"""

from .models import (
    CaptionTrackType,
    CaptionStatus,
    CaptionFormat,
    CaptionQuality,
    CaptionTranslation,
    CaptionDownloadOptions,
    CaptionQualityMetrics,
    CaptionTrack,
    CaptionCue,
    CaptionContent,
    CaptionFilters,
    CaptionAnalytics,
    CaptionResult,
)
from .convert import CaptionFormatConverter
from .analytics import CaptionAnalyzer, CaptionQualityAssessor

__all__ = [
    # enums
    "CaptionTrackType",
    "CaptionStatus",
    "CaptionFormat",
    "CaptionQuality",
    # dataclasses
    "CaptionTranslation",
    "CaptionDownloadOptions",
    "CaptionQualityMetrics",
    "CaptionTrack",
    "CaptionCue",
    "CaptionContent",
    "CaptionFilters",
    "CaptionAnalytics",
    "CaptionResult",
    # converter
    "CaptionFormatConverter",
    # analytics
    "CaptionAnalyzer",
    "CaptionQualityAssessor",
]
