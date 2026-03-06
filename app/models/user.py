"""
User model for SpeechMaster.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.utils.config import GUEST_USER_ID


@dataclass
class User:
    """Represents an application user."""
    id: int = 0
    username: str = ""
    password_hash: str = ""
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_guest: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            id=data.get('id', 0),
            username=data.get('username', ''),
            password_hash=data.get('password_hash', ''),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            is_guest=bool(data.get('is_guest', False)),
        )

    @classmethod
    def guest(cls) -> 'User':
        """Create a guest user instance."""
        return cls(
            id=GUEST_USER_ID,
            username='Guest',
            is_guest=True,
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'is_guest': self.is_guest,
        }
