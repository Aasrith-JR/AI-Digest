"""
Database models for the GUI application.
Handles user authentication, OTP verification, and persona subscriptions.
"""
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncIterator, List, Optional, Dict, Any
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


class UserDatabase:
    """Async database handler for user management."""

    def __init__(self, path: str):
        self.path = path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self.path)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = aiosqlite.Row
        try:
            yield conn
        finally:
            await conn.close()

    async def init_tables(self) -> None:
        """Initialize user management tables."""
        async with self.connect() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_verified BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # OTP table for email verification
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS otp_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    otp_code TEXT NOT NULL,
                    purpose TEXT NOT NULL DEFAULT 'registration',
                    expires_at TIMESTAMP NOT NULL,
                    is_used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User persona subscriptions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_personas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    persona_name TEXT NOT NULL,
                    is_subscribed BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, persona_name)
                )
            """)

            # Sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_otp_email ON otp_codes(email)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_personas_user ON user_personas(user_id)")

            await conn.commit()
            logger.info("User database tables initialized")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, pwd_hash = stored_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except ValueError:
            return False

    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    @staticmethod
    def generate_session_token() -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    # ==================== User Operations ====================

    async def create_user(self, email: str, password: str, is_admin: bool = False) -> Optional[int]:
        """Create a new user (unverified until OTP confirmation)."""
        password_hash = self.hash_password(password)
        async with self.connect() as conn:
            try:
                cursor = await conn.execute(
                    """INSERT INTO users (email, password_hash, is_admin, is_verified)
                       VALUES (?, ?, ?, 0)""",
                    (email.lower(), password_hash, is_admin)
                )
                await conn.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower(),)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def verify_user(self, email: str) -> bool:
        """Mark user as verified."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "UPDATE users SET is_verified = 1, updated_at = ? WHERE email = ?",
                (datetime.utcnow().isoformat(), email.lower())
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def update_password(self, email: str, new_password: str) -> bool:
        """Update user's password."""
        password_hash = self.hash_password(new_password)
        async with self.connect() as conn:
            cursor = await conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE email = ?",
                (password_hash, datetime.utcnow().isoformat(), email.lower())
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def set_admin(self, email: str, is_admin: bool) -> bool:
        """Set user's admin status."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "UPDATE users SET is_admin = ?, updated_at = ? WHERE email = ?",
                (is_admin, datetime.utcnow().isoformat(), email.lower())
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "SELECT id, email, is_admin, is_active, is_verified, created_at FROM users ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_verified_users_with_persona(self, persona_name: str) -> List[Dict[str, Any]]:
        """Get all verified users subscribed to a specific persona.
        Match case-insensitively to avoid mismatches between config keys and persona names.
        """
        async with self.connect() as conn:
            cursor = await conn.execute(
                """SELECT u.id, u.email FROM users u
                   JOIN user_personas up ON u.id = up.user_id
                   WHERE u.is_verified = 1 AND u.is_active = 1 
                   AND UPPER(up.persona_name) = UPPER(?) AND up.is_subscribed = 1""",
                (persona_name,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_all_verified_users(self) -> List[Dict[str, Any]]:
        """Get all verified and active users."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "SELECT id, email FROM users WHERE is_verified = 1 AND is_active = 1"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user and all related data."""
        async with self.connect() as conn:
            cursor = await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # ==================== OTP Operations ====================

    async def create_otp(self, email: str, purpose: str = 'registration',
                         expires_minutes: int = 10) -> str:
        """Create a new OTP for email verification."""
        otp = self.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)

        async with self.connect() as conn:
            # Invalidate old OTPs for this email and purpose
            await conn.execute(
                "UPDATE otp_codes SET is_used = 1 WHERE email = ? AND purpose = ? AND is_used = 0",
                (email.lower(), purpose)
            )
            # Create new OTP
            await conn.execute(
                "INSERT INTO otp_codes (email, otp_code, purpose, expires_at) VALUES (?, ?, ?, ?)",
                (email.lower(), otp, purpose, expires_at.isoformat())
            )
            await conn.commit()
        return otp

    async def verify_otp(self, email: str, otp: str, purpose: str = 'registration') -> bool:
        """Verify an OTP."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                """SELECT id FROM otp_codes 
                   WHERE email = ? AND otp_code = ? AND purpose = ? 
                   AND is_used = 0 AND expires_at > ?""",
                (email.lower(), otp, purpose, datetime.utcnow().isoformat())
            )
            row = await cursor.fetchone()
            if row:
                # Mark OTP as used
                await conn.execute(
                    "UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row['id'],)
                )
                await conn.commit()
                return True
            return False

    # ==================== Session Operations ====================

    async def create_session(self, user_id: int, expires_hours: int = 24) -> str:
        """Create a new session for a user."""
        token = self.generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

        async with self.connect() as conn:
            await conn.execute(
                "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires_at.isoformat())
            )
            await conn.commit()
        return token

    async def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Get session by token."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                """SELECT s.*, u.email, u.is_admin FROM sessions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.session_token = ? AND s.expires_at > ?""",
                (token, datetime.utcnow().isoformat())
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_session(self, token: str) -> bool:
        """Delete a session (logout)."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "DELETE FROM sessions WHERE session_token = ?", (token,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (datetime.utcnow().isoformat(),)
            )
            await conn.commit()
            return cursor.rowcount

    # ==================== Persona Subscription Operations ====================

    async def subscribe_to_persona(self, user_id: int, persona_name: str) -> bool:
        """Subscribe a user to a persona (store normalized to UPPERCASE)."""
        async with self.connect() as conn:
            try:
                await conn.execute(
                    """INSERT INTO user_personas (user_id, persona_name, is_subscribed)
                       VALUES (?, ?, 1)
                       ON CONFLICT(user_id, persona_name) 
                       DO UPDATE SET is_subscribed = 1""",
                    (user_id, persona_name.upper())
                )
                await conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error subscribing to persona: {e}")
                return False

    async def unsubscribe_from_persona(self, user_id: int, persona_name: str) -> bool:
        """Unsubscribe a user from a persona."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "UPDATE user_personas SET is_subscribed = 0 WHERE user_id = ? AND persona_name = ?",
                (user_id, persona_name)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def get_user_personas(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all persona subscriptions for a user."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                "SELECT persona_name, is_subscribed FROM user_personas WHERE user_id = ?",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_user_personas(self, user_id: int, personas: List[str]) -> bool:
        """Update user's persona subscriptions (replaces all current subscriptions).
        Store persona names normalized to UPPERCASE to ensure consistent matching.
        """
        async with self.connect() as conn:
            # Remove all current subscriptions
            await conn.execute(
                "DELETE FROM user_personas WHERE user_id = ?", (user_id,)
            )
            # Add new subscriptions (normalized to UPPER)
            for persona in personas:
                await conn.execute(
                    "INSERT INTO user_personas (user_id, persona_name, is_subscribed) VALUES (?, ?, 1)",
                    (user_id, persona.upper())
                )
            await conn.commit()
            return True
