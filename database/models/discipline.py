from datetime import datetime, timezone, timedelta
from database.connection import acquire
from config import WARN_LIMIT, RESTRICTION_HOURS


async def add_warning(user_id: int, reason: str, issued_by: int) -> int:
    async with acquire() as conn:
        await conn.execute(
            "INSERT INTO warnings (user_id, reason, issued_by) VALUES ($1,$2,$3)",
            user_id, reason, issued_by
        )
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM warnings WHERE user_id=$1 AND is_active=1",
            user_id
        )
        return row["cnt"]


async def remove_warning(user_id: int) -> bool:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM warnings WHERE user_id=$1 AND is_active=1 ORDER BY created_at DESC LIMIT 1",
            user_id
        )
        if not row:
            return False
        await conn.execute("UPDATE warnings SET is_active=0 WHERE id=$1", row["id"])
        return True


async def get_active_warnings(user_id: int):
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM warnings WHERE user_id=$1 AND is_active=1 ORDER BY created_at",
            user_id
        )


async def get_warn_count(user_id: int) -> int:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM warnings WHERE user_id=$1 AND is_active=1",
            user_id
        )
        return row["cnt"]


async def add_restriction(
    user_id: int,
    restriction_type: str = "throttle",
    reason: str = "",
    issued_by: int | None = None,
    hours: int = RESTRICTION_HOURS,
) -> int:
    expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    async with acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO restrictions (user_id, type, reason, issued_by, expires_at) "
            "VALUES ($1,$2,$3,$4,$5) RETURNING id",
            user_id, restriction_type, reason, issued_by, expires
        )
        return row["id"]


async def lift_restriction(user_id: int) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    async with acquire() as conn:
        result = await conn.execute(
            "UPDATE restrictions SET is_active=0, lifted_at=$1 "
            "WHERE user_id=$2 AND is_active=1",
            now, user_id
        )
        count = int(str(result).split()[-1]) if result else 0
        return count > 0


async def get_active_restriction(user_id: int):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM restrictions WHERE user_id=$1 AND is_active=1 "
            "ORDER BY created_at DESC LIMIT 1",
            user_id
        )


async def expire_old_restrictions() -> list[int]:
    now = datetime.now(timezone.utc).isoformat()
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id FROM restrictions "
            "WHERE is_active=1 AND expires_at <= $1",
            now
        )
        if rows:
            await conn.execute(
                "UPDATE restrictions SET is_active=0, lifted_at=$1 "
                "WHERE is_active=1 AND expires_at <= $1",
                now
            )
        return [r["user_id"] for r in rows]


async def get_all_restrictions():
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT r.*, u.full_name, u.telegram_id "
            "FROM restrictions r JOIN users u ON r.user_id=u.telegram_id "
            "WHERE r.is_active=1 ORDER BY r.created_at DESC"
        )


async def get_all_active_warnings():
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT w.*, u.full_name "
            "FROM warnings w JOIN users u ON w.user_id=u.telegram_id "
            "WHERE w.is_active=1 ORDER BY w.created_at DESC"
        )
