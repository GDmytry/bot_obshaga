"""
Dev/SQLite mode for local testing without PostgreSQL.
Creates a thin compatibility layer on top of aiosqlite
so the rest of the codebase doesn't need to change.

Usage: set DEV_MODE=1 in .env, or run with:
  DEV_MODE=1 python main.py
"""
import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_FILE = "bot_data_dev.db"


# ────────────────────────────────────────────────────────────────────────────
# Thin asyncpg-compatible Record wrapper
# ────────────────────────────────────────────────────────────────────────────
class Row(dict):
    """Dict that also supports attribute/index access like asyncpg.Record."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


async def fetchrow(conn, sql: str, *args) -> Row | None:
    sql = _pg2sqlite(sql)
    cursor = await conn.execute(sql, args)
    row = await cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return Row(zip(cols, row))


async def fetch(conn, sql: str, *args) -> list[Row]:
    sql = _pg2sqlite(sql)
    cursor = await conn.execute(sql, args)
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [Row(zip(cols, r)) for r in rows]


async def execute(conn, sql: str, *args) -> str:
    sql = _pg2sqlite(sql)
    cursor = await conn.execute(sql, args)
    await conn.commit()
    return f"OK {cursor.rowcount}"


def _pg2sqlite(sql: str) -> str:
    """Convert $1,$2... placeholders to ? for SQLite."""
    import re
    return re.sub(r'\$\d+', '?', sql)


# ────────────────────────────────────────────────────────────────────────────
# Fake asyncpg Pool backed by aiosqlite
# ────────────────────────────────────────────────────────────────────────────
class FakeConn:
    def __init__(self, conn):
        self._conn = conn

    async def fetchrow(self, sql, *args):
        return await fetchrow(self._conn, sql, *args)

    async def fetch(self, sql, *args):
        return await fetch(self._conn, sql, *args)

    async def execute(self, sql, *args):
        return await execute(self._conn, sql, *args)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakePool:
    def __init__(self, conn):
        self._conn = conn
        self._fake_conn = FakeConn(conn)

    def acquire(self):
        """Returns self (FakeConn) as an async context manager."""
        return self._fake_conn

    async def close(self):
        await self._conn.close()


_pool: FakePool | None = None


async def create_dev_pool():
    global _pool
    conn = await aiosqlite.connect(DB_FILE)
    conn.row_factory = None  # raw tuples, we handle ourselves
    _pool = FakePool(conn)
    logger.info(f"✅ [DEV] SQLite pool created → {DB_FILE}")
    return _pool


def get_dev_pool() -> FakePool:
    if _pool is None:
        raise RuntimeError("Dev pool not initialized")
    return _pool
