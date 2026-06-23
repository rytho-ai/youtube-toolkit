"""
Caption analytics — language detection, reading-speed/gap analysis, quality scoring.

CaptionAnalyzer derives insights from caption content (detected language,
words-per-minute, inter-cue gaps); CaptionQualityAssessor turns a cue list into a
CaptionQualityMetrics score across timing/text/completeness/consistency. Both are
stateless and read only model types.

Reads: typing; .models (CaptionCue, CaptionQuality, CaptionQualityMetrics).
"""

from typing import List, Dict, Any

from .models import CaptionCue, CaptionQuality, CaptionQualityMetrics


class CaptionAnalyzer:
    """Analyze caption content for insights."""

    @staticmethod
    def analyze_language(content: str) -> Dict[str, Any]:
        """Simple language detection based on common words."""
        # Common words in different languages
        language_indicators = {
            'en': ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'],
            'es': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se'],
            'fr': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'],
            'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'],
            'it': ['il', 'di', 'e', 'a', 'in', 'un', 'per', 'è', 'con', 'da'],
            'pt': ['o', 'de', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'não'],
            'ru': ['и', 'в', 'не', 'на', 'я', 'быть', 'с', 'он', 'а', 'как'],
            'ja': ['の', 'に', 'は', 'を', 'が', 'で', 'と', 'も', 'から', 'まで'],
            'ko': ['이', '그', '저', '의', '에', '를', '을', '가', '는', '은'],
            'zh': ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人']
        }

        content_lower = content.lower()
        word_counts = {}

        for lang, words in language_indicators.items():
            count = sum(content_lower.count(word) for word in words)
            word_counts[lang] = count

        # Return language with highest count
        detected_lang = max(word_counts.items(), key=lambda x: x[1])[0]
        confidence = word_counts[detected_lang] / len(content.split()) if content.split() else 0

        return {
            'detected_language': detected_lang,
            'confidence': confidence,
            'word_counts': word_counts
        }

    @staticmethod
    def analyze_reading_speed(cues: List[CaptionCue]) -> Dict[str, float]:
        """Analyze reading speed and timing."""
        if not cues:
            return {'average_wpm': 0.0, 'average_cue_duration': 0.0}

        total_words = sum(len(cue.text.split()) for cue in cues)
        total_duration = sum(cue.duration for cue in cues)

        average_wpm = (total_words / total_duration * 60) if total_duration > 0 else 0.0
        average_cue_duration = total_duration / len(cues)

        return {
            'average_wpm': average_wpm,
            'average_cue_duration': average_cue_duration,
            'total_words': total_words,
            'total_duration': total_duration
        }

    @staticmethod
    def find_gaps(cues: List[CaptionCue], min_gap: float = 0.5) -> List[Dict[str, float]]:
        """Find gaps between caption cues."""
        gaps = []

        for i in range(len(cues) - 1):
            current_end = cues[i].end_time
            next_start = cues[i + 1].start_time

            if next_start - current_end >= min_gap:
                gaps.append({
                    'start': current_end,
                    'end': next_start,
                    'duration': next_start - current_end
                })

        return gaps


class CaptionQualityAssessor:
    """Assess caption quality and provide recommendations."""

    @staticmethod
    def assess_quality(cues: List[CaptionCue], content: str) -> CaptionQualityMetrics:
        """Assess overall caption quality."""
        metrics = CaptionQualityMetrics()

        if not cues:
            metrics.overall_quality = CaptionQuality.POOR
            metrics.issues.append("No caption cues found")
            return metrics

        # Assess timing accuracy
        timing_score = CaptionQualityAssessor._assess_timing_accuracy(cues)
        metrics.timing_accuracy = timing_score

        # Assess text quality
        text_score = CaptionQualityAssessor._assess_text_quality(cues, content)
        metrics.text_quality = text_score

        # Assess completeness
        completeness_score = CaptionQualityAssessor._assess_completeness(cues)
        metrics.completeness = completeness_score

        # Assess consistency
        consistency_score = CaptionQualityAssessor._assess_consistency(cues)
        metrics.consistency = consistency_score

        # Determine overall quality
        avg_score = metrics.average_score
        if avg_score >= 0.9:
            metrics.overall_quality = CaptionQuality.EXCELLENT
        elif avg_score >= 0.7:
            metrics.overall_quality = CaptionQuality.GOOD
        elif avg_score >= 0.5:
            metrics.overall_quality = CaptionQuality.FAIR
        else:
            metrics.overall_quality = CaptionQuality.POOR

        return metrics

    @staticmethod
    def _assess_timing_accuracy(cues: List[CaptionCue]) -> float:
        """Assess timing accuracy (0-1 score)."""
        if not cues:
            return 0.0

        score = 1.0
        issues = 0

        for cue in cues:
            # Check for invalid timing
            if cue.start_time >= cue.end_time:
                issues += 1
                continue

            # Check for very short cues (< 0.5s)
            if cue.duration < 0.5:
                issues += 0.5

            # Check for very long cues (> 10s)
            if cue.duration > 10:
                issues += 0.5

        # Calculate score based on issues
        if issues > 0:
            score = max(0.0, 1.0 - (issues / len(cues)))

        return score

    @staticmethod
    def _assess_text_quality(cues: List[CaptionCue], content: str) -> float:
        """Assess text quality (0-1 score)."""
        if not cues:
            return 0.0

        score = 1.0
        issues = 0

        for cue in cues:
            text = cue.text.strip()

            # Check for empty cues
            if not text:
                issues += 1
                continue

            # Check for very short text
            if len(text) < 2:
                issues += 0.5

            # Check for excessive length
            if len(text) > 200:
                issues += 0.5

            # Check for common issues
            if text.count('\n') > 3:  # Too many line breaks
                issues += 0.3

            if text.count('[') != text.count(']'):  # Unmatched brackets
                issues += 0.2

        # Calculate score based on issues
        if issues > 0:
            score = max(0.0, 1.0 - (issues / len(cues)))

        return score

    @staticmethod
    def _assess_completeness(cues: List[CaptionCue]) -> float:
        """Assess completeness (0-1 score)."""
        if not cues:
            return 0.0

        # Check for gaps
        gaps = CaptionAnalyzer.find_gaps(cues, min_gap=1.0)

        # Calculate completeness based on gaps
        if gaps:
            total_gap_time = sum(gap['duration'] for gap in gaps)
            total_duration = max(cue.end_time for cue in cues)
            gap_ratio = total_gap_time / total_duration if total_duration > 0 else 0
            return max(0.0, 1.0 - gap_ratio)

        return 1.0

    @staticmethod
    def _assess_consistency(cues: List[CaptionCue]) -> float:
        """Assess consistency (0-1 score)."""
        if not cues:
            return 0.0

        # Check duration consistency
        durations = [cue.duration for cue in cues]
        avg_duration = sum(durations) / len(durations)

        # Calculate variance
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        std_dev = variance ** 0.5

        # Score based on consistency (lower std dev = higher score)
        consistency_score = max(0.0, 1.0 - (std_dev / avg_duration) if avg_duration > 0 else 0)

        return consistency_score
