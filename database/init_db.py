import os
import logging
from database.connection import get_pool

logger = logging.getLogger(__name__)
DEV_MODE: bool = os.getenv("DEV_MODE", "0") == "1"


async def init_db() -> None:
    """Create all tables. Uses SQLite-compatible DDL in DEV_MODE."""
    pool = get_pool()

    if DEV_MODE:
        await _init_sqlite(pool)
    else:
        await _init_postgres(pool)


async def _init_sqlite(pool) -> None:
    """SQLite DDL — simplified types for local dev testing."""
    conn = pool._conn
    stmts = [
        """CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            current_user_index INTEGER DEFAULT 0,
            UNIQUE(chat_id, name)
        )""",
        """CREATE TABLE IF NOT EXISTS queue_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL REFERENCES queues(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            is_done INTEGER DEFAULT 0,
            done_time TEXT,
            UNIQUE(queue_id, user_id)
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            mac_addresses TEXT DEFAULT '',
            status TEXT DEFAULT 'away',
            last_seen TEXT,
            is_active INTEGER DEFAULT 1,
            registered_at TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS expense_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
            debtor_id INTEGER NOT NULL,
            amount REAL NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            issued_by INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS restrictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'throttle',
            reason TEXT,
            issued_by INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT,
            lifted_at TEXT,
            is_active INTEGER DEFAULT 1
        )""",
        """CREATE TABLE IF NOT EXISTS presence_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event TEXT NOT NULL,
            logged_at TEXT DEFAULT (datetime('now'))
        )""",
    ]
    for stmt in stmts:
        await conn.execute(stmt)
    await conn.commit()
    logger.info("✅ [DEV] SQLite tables initialized.")


async def _init_postgres(pool) -> None:
    """Full PostgreSQL DDL."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS queues (
                id          SERIAL PRIMARY KEY,
                chat_id     BIGINT NOT NULL,
                name        TEXT   NOT NULL,
                current_user_index INTEGER DEFAULT 0,
                UNIQUE(chat_id, name)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS queue_members (
                id          SERIAL PRIMARY KEY,
                queue_id    INTEGER NOT NULL REFERENCES queues(id) ON DELETE CASCADE,
                user_id     BIGINT  NOT NULL,
                user_name   TEXT    NOT NULL,
                order_index INTEGER NOT NULL,
                is_done     BOOLEAN DEFAULT FALSE,
                done_time   TEXT,
                UNIQUE(queue_id, user_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              SERIAL PRIMARY KEY,
                telegram_id     BIGINT UNIQUE NOT NULL,
                username        TEXT,
                full_name       TEXT NOT NULL,
                mac_addresses   TEXT DEFAULT '',
                status          TEXT DEFAULT 'away',
                last_seen       TIMESTAMPTZ,
                is_active       BOOLEAN DEFAULT TRUE,
                registered_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          SERIAL PRIMARY KEY,
                payer_id    BIGINT NOT NULL REFERENCES users(telegram_id),
                amount      NUMERIC(10,2) NOT NULL,
                description TEXT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expense_splits (
                id          SERIAL PRIMARY KEY,
                expense_id  INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
                debtor_id   BIGINT  NOT NULL REFERENCES users(telegram_id),
                amount      NUMERIC(10,2) NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT  NOT NULL REFERENCES users(telegram_id),
                reason      TEXT    NOT NULL,
                issued_by   BIGINT  NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                is_active   BOOLEAN DEFAULT TRUE
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS restrictions (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT  NOT NULL REFERENCES users(telegram_id),
                type        TEXT    NOT NULL DEFAULT 'throttle',
                reason      TEXT,
                issued_by   BIGINT,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                expires_at  TIMESTAMPTZ,
                lifted_at   TIMESTAMPTZ,
                is_active   BOOLEAN DEFAULT TRUE
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS presence_log (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL REFERENCES users(telegram_id),
                event       TEXT NOT NULL,
                logged_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    logger.info("✅ PostgreSQL tables initialized.")
