"""
Input validation utilities for SpeechMaster.
"""
import re
from app.utils.config import (
    USERNAME_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_PATTERN,
)


def validate_username(username: str) -> tuple:
    """
    Validate username input.

    Rules:
        - Length: 3-20 characters
        - Characters: a-z, A-Z, 0-9, underscore
        - Cannot start with number
        - No spaces

    Returns:
        (is_valid, error_message)
    """
    if not username:
        return False, "Username is required."

    username = username.strip()

    if len(username) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters."

    if len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username must be at most {USERNAME_MAX_LENGTH} characters."

    if ' ' in username:
        return False, "Username cannot contain spaces."

    if not re.match(USERNAME_PATTERN, username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores."

    return True, ""


def validate_password(password: str) -> tuple:
    """
    Validate password input.

    Rules:
        - Minimum 6 characters

    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password is required."

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters."

    return True, ""


def validate_passwords_match(password: str, confirm_password: str) -> tuple:
    """
    Check that password and confirmation match.

    Returns:
        (is_valid, error_message)
    """
    if password != confirm_password:
        return False, "Passwords do not match."
    return True, ""


def password_strength(password: str) -> str:
    """
    Evaluate password strength.

    Returns:
        'weak', 'medium', or 'strong'
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return 'weak'

    score = 0
    if len(password) >= 8:
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[^a-zA-Z0-9]', password):
        score += 1

    if score >= 3:
        return 'strong'
    elif score >= 1:
        return 'medium'
    return 'weak'
