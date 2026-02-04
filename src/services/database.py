import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncIterator, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, path: str):
        self.path = path

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        conn = await aiosqlite.connect(self.path)
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
        finally:
            await conn.close()

    async def execute(self, query: str, params: tuple = ()) -> None:
        async with self.connect() as conn:
            await conn.execute(query, params)
            await conn.commit()

    async def fetchone(self, query: str, params: tuple = ()):
        async with self.connect() as conn:
            cursor = await conn.execute(query, params)
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):
        async with self.connect() as conn:
            cursor = await conn.execute(query, params)
            return await cursor.fetchall()

    async def init_tables(self) -> None:
        """Initialize database tables for digest tracking."""
        async with self.connect() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    relevance_score REAL,
                    persona TEXT NOT NULL,
                    faiss_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_digests_url ON sent_digests(url)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_digests_sent_at ON sent_digests(sent_at)
            """)
            await conn.commit()
            logger.info("Database tables initialized")

    async def is_url_sent(self, url: str, hours: int = 48) -> bool:
        """Check if URL was already sent within the specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        result = await self.fetchone(
            "SELECT 1 FROM sent_digests WHERE url = ? AND sent_at > ?",
            (url, cutoff.isoformat())
        )
        return result is not None

    async def get_recent_faiss_ids(self, hours: int = 48) -> List[int]:
        """Get FAISS IDs of digests sent within the specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        rows = await self.fetchall(
            "SELECT faiss_id FROM sent_digests WHERE sent_at > ? AND faiss_id IS NOT NULL",
            (cutoff.isoformat(),)
        )
        return [row[0] for row in rows]

    async def add_sent_digest(
        self,
        url: str,
        title: str,
        persona: str,
        relevance_score: Optional[float] = None,
        faiss_id: Optional[int] = None,
    ) -> int:
        """Record a sent digest in the database."""
        async with self.connect() as conn:
            cursor = await conn.execute(
                """
                INSERT OR REPLACE INTO sent_digests 
                (url, title, relevance_score, persona, faiss_id, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (url, title, relevance_score, persona, faiss_id, datetime.utcnow().isoformat())
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_recent_digests(
        self,
        hours: int = 48,
        persona: Optional[str] = None
    ) -> List[Tuple[int, str, str, float, str]]:
        """Get digests sent within the specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        if persona:
            rows = await self.fetchall(
                """SELECT id, url, title, relevance_score, persona 
                   FROM sent_digests 
                   WHERE sent_at > ? AND persona = ?
                   ORDER BY sent_at DESC""",
                (cutoff.isoformat(), persona)
            )
        else:
            rows = await self.fetchall(
                """SELECT id, url, title, relevance_score, persona 
                   FROM sent_digests 
                   WHERE sent_at > ?
                   ORDER BY sent_at DESC""",
                (cutoff.isoformat(),)
            )
        return rows

    async def cleanup_old_digests(self, days: int = 30) -> int:
        """Remove digests older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with self.connect() as conn:
            cursor = await conn.execute(
                "DELETE FROM sent_digests WHERE sent_at < ?",
                (cutoff.isoformat(),)
            )
            await conn.commit()
            return cursor.rowcount

