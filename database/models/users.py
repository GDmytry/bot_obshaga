from database.connection import acquire


async def register_user(telegram_id: int, username: str | None, full_name: str) -> bool:
    async with acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id=$1", telegram_id
        )
        if existing:
            await conn.execute(
                "UPDATE users SET username=$1, full_name=$2, is_active=TRUE WHERE telegram_id=$3",
                username, full_name, telegram_id
            )
            return False
        await conn.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES ($1,$2,$3)",
            telegram_id, username, full_name
        )
        return True


async def get_user(telegram_id: int):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id=$1", telegram_id
        )


async def get_all_active_users():
    async with acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM users WHERE is_active=TRUE ORDER BY full_name"
        )


async def get_user_by_username(username: str):
    async with acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE lower(username)=lower($1)", username
        )
