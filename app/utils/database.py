"""
SQLite database operations for SpeechMaster.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

from app.utils.config import DB_PATH, DATA_DIR, RESOURCES_DIR, DATABASE_CACHE_SIZE

logger = logging.getLogger(__name__)


class Database:
    """SQLite database wrapper with connection management."""

    _instance: Optional['Database'] = None

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self._connection: Optional[sqlite3.Connection] = None

    @classmethod
    def get_instance(cls, db_path: Path = None) -> 'Database':
        """Get singleton database instance."""
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def connect(self) -> sqlite3.Connection:
        """Open database connection."""
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute(f"PRAGMA cache_size={DATABASE_CACHE_SIZE}")
            self._connection.execute("PRAGMA foreign_keys=ON")
            logger.info("Database connected: %s", self.db_path)
        return self._connection

    @property
    def conn(self) -> sqlite3.Connection:
        return self.connect()

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed.")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def init_database(self):
        """Create tables if they don't exist."""
        conn = self.conn
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_guest BOOLEAN DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sentences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                difficulty_level INTEGER DEFAULT 1,
                category TEXT,
                word_count INTEGER,
                phoneme_complexity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sentence_id INTEGER NOT NULL,
                audio_file_path TEXT NOT NULL,
                transcription TEXT,
                target_text TEXT,
                wer_score REAL,
                accuracy_percentage INTEGER,
                score_category TEXT,
                duration_seconds REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (sentence_id) REFERENCES sentences(id)
            );

            CREATE INDEX IF NOT EXISTS idx_recordings_user_id
                ON recordings(user_id);
            CREATE INDEX IF NOT EXISTS idx_recordings_date
                ON recordings(recorded_at DESC);
            CREATE INDEX IF NOT EXISTS idx_sentences_difficulty
                ON sentences(difficulty_level);
        """)

        # Ensure default guest user exists for recording evaluations mapping to user_id=1
        cursor.execute("INSERT OR IGNORE INTO users (id, username, password_hash, is_guest) VALUES (1, 'guest', 'guest_hash', 1)")

        conn.commit()
        logger.info("Database schema initialized.")

    def populate_sentences(self):
        """Load sentences from JSON into database if table is empty."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sentences")
        count = cursor.fetchone()[0]

        if count > 0:
            logger.info("Sentences already populated (%d rows).", count)
            return

        json_path = RESOURCES_DIR / "sentences" / "sentence_library.json"
        if not json_path.exists():
            logger.warning("Sentence library not found at %s", json_path)
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        sentences = data.get('sentences', [])
        for s in sentences:
            cursor.execute(
                "INSERT INTO sentences (text, difficulty_level, category, word_count) VALUES (?, ?, ?, ?)",
                (s['text'], s.get('difficulty', 1), s.get('category', ''), s.get('word_count', len(s['text'].split())))
            )

        self.conn.commit()
        logger.info("Populated %d sentences from JSON.", len(sentences))

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def create_user(self, username: str, password_hash: str) -> int:
        """Insert a new user and return their id."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Retrieve user row by username."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Retrieve user row by id."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_last_login(self, user_id: int):
        """Update user's last_login timestamp."""
        self.conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Sentences
    # ------------------------------------------------------------------
    def get_all_sentences(self) -> list:
        """Return all sentences."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sentences ORDER BY difficulty_level, id")
        return [dict(row) for row in cursor.fetchall()]

    def get_sentences_by_difficulty(self, level: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM sentences WHERE difficulty_level = ? ORDER BY id",
            (level,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_sentence_by_id(self, sentence_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sentences WHERE id = ?", (sentence_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Recordings
    # ------------------------------------------------------------------
    def save_recording(self, user_id: int, sentence_id: int,
                       audio_file_path: str, transcription: str,
                       target_text: str, wer_score: float,
                       accuracy_percentage: int, score_category: str,
                       duration_seconds: float) -> int:
        """Insert a recording and return its id."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO recordings
               (user_id, sentence_id, audio_file_path, transcription,
                target_text, wer_score, accuracy_percentage, score_category,
                duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, sentence_id, audio_file_path, transcription,
             target_text, wer_score, accuracy_percentage, score_category,
             duration_seconds),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recordings_for_user(self, user_id: int, limit: int = 100,
                                category: str = None,
                                order_by: str = 'recorded_at DESC') -> list:
        """Fetch recordings for a given user."""
        query = "SELECT * FROM recordings WHERE user_id = ?"
        params: list[Any] = [user_id]

        if category:
            query += " AND score_category = ?"
            params.append(category)

        # Whitelist ordering
        allowed_orders = {
            'recorded_at DESC': 'recorded_at DESC',
            'accuracy_percentage DESC': 'accuracy_percentage DESC',
            'accuracy_percentage ASC': 'accuracy_percentage ASC',
        }
        order = allowed_orders.get(order_by, 'recorded_at DESC')
        query += f" ORDER BY {order} LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_recording_by_id(self, recording_id: int) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_recording(self, recording_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_user_stats(self, user_id: int) -> dict:
        """Aggregate statistics for a user."""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) as total FROM recordings WHERE user_id = ?",
            (user_id,),
        )
        total = cursor.fetchone()['total']

        cursor.execute(
            "SELECT AVG(accuracy_percentage) as avg_score FROM recordings WHERE user_id = ?",
            (user_id,),
        )
        avg_row = cursor.fetchone()
        avg_score = round(avg_row['avg_score']) if avg_row['avg_score'] is not None else 0

        cursor.execute(
            "SELECT score_category, COUNT(*) as cnt FROM recordings WHERE user_id = ? GROUP BY score_category",
            (user_id,),
        )
        categories = {row['score_category']: row['cnt'] for row in cursor.fetchall()}

        return {
            'total_sessions': total,
            'average_score': avg_score,
            'excellent': categories.get('excellent', 0),
            'good': categories.get('good', 0),
            'needs_improvement': categories.get('needs_improvement', 0),
        }


def init_database(db_path: Path = None):
    """Convenience function to initialise the DB and seed data."""
    db = Database.get_instance(db_path)
    db.init_database()
    db.populate_sentences()
    return db
