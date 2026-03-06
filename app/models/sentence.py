"""
Sentence model for SpeechMaster.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Sentence:
    """Represents a practice sentence."""
    id: int = 0
    text: str = ""
    difficulty_level: int = 1       # 1=Easy, 2=Medium, 3=Hard
    category: str = ""
    word_count: int = 0
    phoneme_complexity: Optional[float] = None

    DIFFICULTY_LABELS = {1: "Easy", 2: "Medium", 3: "Hard"}
    DIFFICULTY_COLORS = {1: "#34A853", 2: "#FBBC04", 3: "#EA4335"}

    @classmethod
    def from_dict(cls, data: dict) -> 'Sentence':
        return cls(
            id=data.get('id', 0),
            text=data.get('text', ''),
            difficulty_level=data.get('difficulty_level', 1),
            category=data.get('category', ''),
            word_count=data.get('word_count', 0),
            phoneme_complexity=data.get('phoneme_complexity'),
        )

    @property
    def difficulty_label(self) -> str:
        return self.DIFFICULTY_LABELS.get(self.difficulty_level, "Unknown")

    @property
    def difficulty_color(self) -> str:
        return self.DIFFICULTY_COLORS.get(self.difficulty_level, "#5F6368")

    @property
    def preview(self) -> str:
        """Return a truncated preview (max 60 chars)."""
        if len(self.text) <= 60:
            return self.text
        return self.text[:57] + "..."
