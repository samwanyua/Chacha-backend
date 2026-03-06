"""
Recording model for SpeechMaster.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Recording:
    """Represents a speech recording and its scoring result."""
    id: int = 0
    user_id: int = 0
    sentence_id: int = 0
    audio_file_path: str = ""
    transcription: str = ""
    target_text: str = ""
    wer_score: float = 0.0
    accuracy_percentage: int = 0
    score_category: str = ""
    duration_seconds: float = 0.0
    recorded_at: Optional[datetime] = None

    CATEGORY_COLORS = {
        'excellent': '#34A853',
        'good': '#FBBC04',
        'needs_improvement': '#EA4335',
    }

    CATEGORY_LABELS = {
        'excellent': 'Excellent',
        'good': 'Good',
        'needs_improvement': 'Needs Improvement',
    }

    @classmethod
    def from_dict(cls, data: dict) -> 'Recording':
        return cls(
            id=data.get('id', 0),
            user_id=data.get('user_id', 0),
            sentence_id=data.get('sentence_id', 0),
            audio_file_path=data.get('audio_file_path', ''),
            transcription=data.get('transcription', ''),
            target_text=data.get('target_text', ''),
            wer_score=data.get('wer_score', 0.0),
            accuracy_percentage=data.get('accuracy_percentage', 0),
            score_category=data.get('score_category', ''),
            duration_seconds=data.get('duration_seconds', 0.0),
            recorded_at=data.get('recorded_at'),
        )

    @property
    def category_label(self) -> str:
        return self.CATEGORY_LABELS.get(self.score_category, 'Unknown')

    @property
    def category_color(self) -> str:
        return self.CATEGORY_COLORS.get(self.score_category, '#5F6368')

    @property
    def date_display(self) -> str:
        if isinstance(self.recorded_at, str):
            return self.recorded_at[:16].replace('T', ' ')
        if isinstance(self.recorded_at, datetime):
            return self.recorded_at.strftime('%Y-%m-%d %H:%M')
        return ''

    @property
    def target_preview(self) -> str:
        """Truncated target text for list views."""
        if len(self.target_text) <= 50:
            return self.target_text
        return self.target_text[:47] + "..."
