import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator


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
