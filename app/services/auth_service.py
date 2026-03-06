"""
Authentication service for SpeechMaster.
Handles user registration, login, guest mode, and session management.
"""
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import bcrypt

from app.models.user import User
from app.utils.config import DATA_DIR, GUEST_USER_ID
from app.utils.database import Database
from app.utils.validators import validate_username, validate_password, validate_passwords_match

logger = logging.getLogger(__name__)


class AuthService:
    """Manages user authentication and sessions."""

    def __init__(self, db: Database):
        self.db = db
        self._current_user: Optional[User] = None
        self._guest_temp_dir: Optional[str] = None

    @property
    def current_user(self) -> Optional[User]:
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        return self._current_user is not None

    @property
    def is_guest(self) -> bool:
        return self._current_user is not None and self._current_user.is_guest

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register_user(self, username: str, password: str, confirm_password: str) -> dict:
        """
        Register a new user.

        Returns:
            {'success': bool, 'user_id': int, 'message': str}
        """
        # Validate username
        valid, msg = validate_username(username)
        if not valid:
            return {'success': False, 'user_id': 0, 'message': msg}

        # Validate password
        valid, msg = validate_password(password)
        if not valid:
            return {'success': False, 'user_id': 0, 'message': msg}

        # Confirm match
        valid, msg = validate_passwords_match(password, confirm_password)
        if not valid:
            return {'success': False, 'user_id': 0, 'message': msg}

        # Check uniqueness
        existing = self.db.get_user_by_username(username)
        if existing:
            return {'success': False, 'user_id': 0, 'message': "Username already exists. Please choose another."}

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

        try:
            user_id = self.db.create_user(username, password_hash)
        except Exception as e:
            logger.error("Failed to create user: %s", e)
            return {'success': False, 'user_id': 0, 'message': "Registration failed. Please try again."}

        # Create user recording directory
        user_dir = DATA_DIR / "users" / f"user_{user_id}" / "recordings"
        user_dir.mkdir(parents=True, exist_ok=True)

        logger.info("User registered: %s (id=%d)", username, user_id)
        return {'success': True, 'user_id': user_id, 'message': "Account created successfully!"}

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login_user(self, username: str, password: str) -> dict:
        """
        Authenticate user.

        Returns:
            {'success': bool, 'user_id': int, 'username': str, 'message': str}
        """
        if not username or not password:
            return {'success': False, 'user_id': 0, 'username': '', 'message': "Please enter both username and password."}

        user_data = self.db.get_user_by_username(username)
        if not user_data:
            return {'success': False, 'user_id': 0, 'username': '', 'message': "Invalid username or password."}

        stored_hash = user_data['password_hash'].encode('utf-8')
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return {'success': False, 'user_id': 0, 'username': '', 'message': "Invalid username or password."}

        # Update last login
        self.db.update_last_login(user_data['id'])

        # Set current user
        self._current_user = User.from_dict(user_data)
        logger.info("User logged in: %s", username)

        return {
            'success': True,
            'user_id': user_data['id'],
            'username': user_data['username'],
            'message': "Login successful!",
        }

    # ------------------------------------------------------------------
    # Guest Mode
    # ------------------------------------------------------------------
    def create_guest_session(self) -> dict:
        """
        Create a temporary guest session.

        Returns:
            {'user_id': int, 'username': str, 'is_guest': True}
        """
        self._guest_temp_dir = tempfile.mkdtemp(prefix='speechmaster_guest_')
        guest = User.guest()
        self._current_user = guest

        logger.info("Guest session created. Temp dir: %s", self._guest_temp_dir)
        return {
            'user_id': guest.id,
            'username': guest.username,
            'is_guest': True,
        }

    def get_guest_recording_dir(self) -> str:
        """Get temp directory for guest recordings."""
        if self._guest_temp_dir:
            rec_dir = os.path.join(self._guest_temp_dir, 'recordings')
            os.makedirs(rec_dir, exist_ok=True)
            return rec_dir
        return tempfile.mkdtemp(prefix='speechmaster_guest_rec_')

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    def logout(self):
        """Log out current user and clean up."""
        if self._current_user:
            username = self._current_user.username
            is_guest = self._current_user.is_guest

            if is_guest and self._guest_temp_dir:
                # Clean up guest temp files
                try:
                    shutil.rmtree(self._guest_temp_dir, ignore_errors=True)
                    logger.info("Cleaned up guest temp dir: %s", self._guest_temp_dir)
                except Exception as e:
                    logger.warning("Failed to clean up guest dir: %s", e)
                self._guest_temp_dir = None

            self._current_user = None
            logger.info("User logged out: %s (guest=%s)", username, is_guest)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_user_recording_dir(self) -> str:
        """Get recording directory for current user."""
        if not self._current_user:
            raise RuntimeError("No user is logged in.")

        if self._current_user.is_guest:
            return self.get_guest_recording_dir()

        user_dir = DATA_DIR / "users" / f"user_{self._current_user.id}" / "recordings"
        user_dir.mkdir(parents=True, exist_ok=True)
        return str(user_dir)
