import os
import logging

logger = logging.getLogger(__name__)

DEV_MODE: bool = os.getenv("DEV_MODE", "0") == "1"

_pool = None


async def create_pool():
    global _pool
    if DEV_MODE:
        from dev_sqlite import create_dev_pool
        _pool = await create_dev_pool()
        logger.info("✅ [DEV] Running with SQLite — no PostgreSQL needed.")
        return _pool

    import asyncpg
    from config import DB_DSN
    _pool = await asyncpg.create_pool(dsn=DB_DSN, min_size=2, max_size=10)
    logger.info("✅ PostgreSQL connection pool created.")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        logger.info("DB pool closed.")


def get_pool():
    if _pool is None:
        raise RuntimeError("DB pool is not initialized. Call create_pool() first.")
    return _pool


def acquire():
    """
    Returns an async context manager for a DB connection.
    Usage:
        async with acquire() as conn:
            row = await conn.fetchrow(...)

    In DEV_MODE: returns FakeConn (aiosqlite-backed).
    In production: acquires a real asyncpg connection from pool.
    """
    return get_pool().acquire()
